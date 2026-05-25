#!/usr/bin/env python3
"""Xdclaw multimodal image tool layer.

Keeps VLM / image generation outside the main session. Reads New API settings
from the local OpenClaw config, calls OpenAI-compatible endpoints, and prints
plain results for the agent to relay.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

# Default Feishu open_id for auto-notifying after image generation
# Set via FEISHU_NOTIFY_OPEN_ID env var; empty string disables auto-send
FEISHU_NOTIFY_OPEN_ID = os.environ.get("FEISHU_NOTIFY_OPEN_ID", "ou_5cc59c09e86ae9f0e57effc77f9fdd38")

DEFAULT_CONFIGS = [
    "/root/.openclaw/openclaw.json",
    "/root/clawd/.openclaw/openclaw.json",
    os.path.expanduser("~/.openclaw/openclaw.json"),
]


def load_provider(provider: str = "xdclaw-pool") -> tuple[str, str]:
    for p in DEFAULT_CONFIGS:
        try:
            data = json.loads(Path(p).read_text())
        except Exception:
            continue
        prov = (((data.get("models") or {}).get("providers") or {}).get(provider) or {})
        base = prov.get("baseUrl") or prov.get("base_url")
        key = prov.get("apiKey") or prov.get("api_key")
        if base and key:
            return base.rstrip("/"), key
    raise SystemExit("ERROR: cannot find xdclaw-pool baseUrl/apiKey in OpenClaw config")


def request_json(url: str, key: str, payload: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise SystemExit(f"ERROR HTTP {e.code}: {body[:2000]}")


def request_multipart(url: str, key: str, fields: dict[str, str], files: list[tuple[str, Path]], timeout: int = 180) -> dict[str, Any]:
    boundary = "----xdclaw" + uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode("utf-8"))
    for name, path in files:
        if not path.exists():
            raise SystemExit(f"ERROR: file not found: {path}")
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        data = path.read_bytes()
        parts.append((
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8") + data + b"\r\n")
    parts.append((f"--{boundary}--\r\n").encode("utf-8"))
    req = urllib.request.Request(
        url,
        data=b"".join(parts),
        headers={"Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise SystemExit(f"ERROR HTTP {e.code}: {body[:2000]}")


def image_to_url(value: str) -> str:
    if value.startswith(("http://", "https://", "data:image/")):
        return value
    path = Path(value).expanduser()
    if not path.exists():
        raise SystemExit(f"ERROR: image not found: {value}")
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def understand(args: argparse.Namespace) -> None:
    base, key = load_provider(args.provider)
    content: list[dict[str, Any]] = [{"type": "text", "text": args.prompt}]
    for img in args.image:
        content.append({"type": "image_url", "image_url": {"url": image_to_url(img)}})
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }
    data = request_json(f"{base}/chat/completions", key, payload, timeout=args.timeout)
    msg = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    print(msg.strip() or json.dumps(data, ensure_ascii=False))


def download(url: str, out_path: Path, timeout: int = 120) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "xdclaw-mm-image/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out_path.write_bytes(r.read())


def feishu_send_image(image_path: str, open_id: str) -> bool:
    """Upload image to Feishu and send as native image message."""
    # Try to read app credentials from config
    app_id = ""
    app_secret = ""
    for p in DEFAULT_CONFIGS:
        try:
            data = json.loads(Path(p).read_text())
            feishu_cfg = ((data.get("channels") or {}).get("feishu") or {})
            app_id = feishu_cfg.get("appId") or ""
            app_secret = feishu_cfg.get("appSecret") or ""
            if app_id and app_secret:
                break
        except Exception:
            continue
    if not app_id or not app_secret:
        print("WARN: feishu appId/appSecret not found in config", file=sys.stderr)
        return False

    # 1. Get tenant access token
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            token_data = json.loads(r.read().decode())
        token = token_data.get("tenant_access_token")
        if not token:
            print(f"WARN: feishu auth failed: {token_data}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"WARN: feishu token error: {e}", file=sys.stderr)
        return False

    # 2. Upload image
    boundary = "----xdclawFeishu" + uuid.uuid4().hex
    img_path = Path(image_path)
    img_data = img_path.read_bytes()
    body_parts = []
    body_parts.append(f"--{boundary}".encode())
    body_parts.append(b'Content-Disposition: form-data; name="image_type"')
    body_parts.append(b"")
    body_parts.append(b"message")
    body_parts.append(f"--{boundary}".encode())
    body_parts.append(f'Content-Disposition: form-data; name="image"; filename="{img_path.name}"'.encode())
    body_parts.append(b"Content-Type: image/png")
    body_parts.append(b"")
    body_parts.append(img_data)
    body_parts.append(f"--{boundary}--".encode())
    body = b"\r\n".join(body_parts)

    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/images",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            upload_resp = json.loads(r.read().decode())
        image_key = (upload_resp.get("data") or {}).get("image_key")
        if not image_key:
            print(f"WARN: feishu upload failed: {upload_resp}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"WARN: feishu upload error: {e}", file=sys.stderr)
        return False

    # 3. Send image message
    payload = json.dumps({
        "receive_id": open_id,
        "msg_type": "image",
        "content": json.dumps({"image_key": image_key}),
    }).encode()
    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            send_resp = json.loads(r.read().decode())
        if send_resp.get("code") != 0:
            print(f"WARN: feishu send failed: {send_resp}", file=sys.stderr)
            return False
        print(f"[feishu] image sent to {open_id}: {image_key}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"WARN: feishu send error: {e}", file=sys.stderr)
        return False


def save_image_response(data: dict[str, Any], out_dir: Path, model: str, timeout: int = 180, notify_feishu: str | None = None) -> list[str]:
    """Save generated images; if notify_feishu is an open_id, auto-send each image."""
    items = data.get("data") or []
    if not items:
        raise SystemExit("ERROR: image operation returned no data: " + json.dumps(data, ensure_ascii=False)[:2000])
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for i, item in enumerate(items):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe_model = model.replace('/', '-')
        if item.get("b64_json"):
            out = out_dir / f"{safe_model}-{stamp}-{i}.png"
            out.write_bytes(base64.b64decode(item["b64_json"]))
            saved.append(str(out))
        elif item.get("url"):
            parsed = urllib.parse.urlparse(item["url"])
            ext = Path(parsed.path).suffix or ".png"
            out = out_dir / f"{safe_model}-{stamp}-{i}{ext}"
            download(item["url"], out, timeout=timeout)
            saved.append(str(out))
        else:
            raise SystemExit("ERROR: unsupported image payload: " + json.dumps(item, ensure_ascii=False)[:1000])
        # Auto-send to Feishu if configured
        if notify_feishu:
            feishu_send_image(str(out), notify_feishu)
    return saved


def generate(args: argparse.Namespace) -> None:
    base, key = load_provider(args.provider)
    payload: dict[str, Any] = {"model": args.model, "prompt": args.prompt, "n": max(1, min(args.n, 4)), "size": args.size}
    if args.quality:
        payload["quality"] = args.quality
    if args.response_format:
        payload["response_format"] = args.response_format
    data = request_json(f"{base}/images/generations", key, payload, timeout=args.timeout)
    notify_to = args.notify_feishu or FEISHU_NOTIFY_OPEN_ID
    for p in save_image_response(data, Path(args.out).expanduser(), args.model, timeout=args.timeout, notify_feishu=notify_to if not args.no_notify else None):
        print(p)


def edit_image(args: argparse.Namespace) -> None:
    base, key = load_provider(args.provider)
    fields: dict[str, str] = {"model": args.model, "prompt": args.prompt, "size": args.size}
    if args.quality:
        fields["quality"] = args.quality
    if args.response_format:
        fields["response_format"] = args.response_format
    files: list[tuple[str, Path]] = [("image", Path(img).expanduser()) for img in args.image[:4]]
    if len(args.image) > 4:
        print(f"WARN: received {len(args.image)} images, using first 4", file=sys.stderr)
    if args.mask:
        files.append(("mask", Path(args.mask).expanduser()))
    data = request_multipart(f"{base}/images/edits", key, fields, files, timeout=args.timeout)
    notify_to = args.notify_feishu or FEISHU_NOTIFY_OPEN_ID
    for p in save_image_response(data, Path(args.out).expanduser(), args.model, timeout=args.timeout, notify_feishu=notify_to if not args.no_notify else None):
        print(p)


# === ASYNC ENQUEUE (xdclaw async-runtime entrypoint) ===
def enqueue(args: argparse.Namespace) -> None:
    """Append an async image-generation request to the local queue file.

    The host-side router (xd_generic_image_router.py) discovers this file at
    /opt/xdclaw/users/<container>/workspace/.xdclaw-async-image-queue.jsonl,
    enqueues an image.generate task, and the worker invokes mm_image.py generate
    in this same container, with results pushed back via the owning channel.

    The agent should call this and immediately reply "任务已派发，处理中…" without
    waiting for the image; final delivery is handled by async-runtime.
    """
    queue_path = Path(args.queue or "/root/clawd/.xdclaw-async-image-queue.jsonl")
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    request_id = args.request_id or f"req_{uuid.uuid4().hex[:16]}"
    target = args.target
    if not target:
        if not args.sender_id:
            raise SystemExit("ERROR: --sender-id or --target is required")
        if args.type == "group":
            target = f"group:{args.sender_id}"
        else:
            target = f"c2c:{args.sender_id}"
    record = {
        "request_id": request_id,
        "ts": int(time.time() * 1000),
        "channel": args.channel,
        "senderId": args.sender_id,
        "target": target,
        "type": args.type,
        "prompt": args.prompt,
    }
    if args.n and args.n > 1:
        record["n"] = args.n
    if getattr(args, 'session_id', None):
        record["sessionId"] = args.session_id
    with queue_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({
        "ok": True,
        "request_id": request_id,
        "queue": str(queue_path),
        "channel": args.channel,
        "target": target,
        "note": "async task queued; final image will be pushed via async-runtime",
    }, ensure_ascii=False))



def main() -> None:
    parser = argparse.ArgumentParser(description="Xdclaw multimodal image tool layer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("understand", help="analyze images with a VLM")
    p.add_argument("--image", action="append", required=True, help="local image path, URL, or data:image URL")
    p.add_argument("--prompt", required=True)
    p.add_argument("--model", default="qwen3.6-plus")
    p.add_argument("--provider", default="xdclaw-pool")
    p.add_argument("--max-tokens", type=int, default=1200)
    p.add_argument("--temperature", type=float, default=0)
    p.add_argument("--timeout", type=int, default=120)
    p.set_defaults(func=understand)

    p = sub.add_parser("generate", help="generate an image")
    p.add_argument("--prompt", required=True)
    p.add_argument("--model", default="gpt-image-2")
    p.add_argument("--provider", default="xdclaw-pool")
    p.add_argument("--size", default="1024x1024")
    p.add_argument("--n", type=int, default=1, help="number of images to generate, capped at 4")
    p.add_argument("--quality", default=None)
    p.add_argument("--response-format", default=None)
    p.add_argument("--out", default="/root/.openclaw/media/qqbot/outputs")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--notify-feishu", default=None, help="open_id to auto-send image via Feishu native API after generation")
    p.add_argument("--no-notify", action="store_true", help="disable auto-send to Feishu even if FEISHU_NOTIFY_OPEN_ID is set")
    p.set_defaults(func=generate)

    p = sub.add_parser("edit", help="edit an existing image")
    p.add_argument("--image", action="append", required=True, help="local source image path; repeat up to 4 times")
    p.add_argument("--prompt", required=True)
    p.add_argument("--model", default="gpt-image-2")
    p.add_argument("--provider", default="xdclaw-pool")
    p.add_argument("--size", default="1024x1024")
    p.add_argument("--n", type=int, default=1, help="number of images to generate, capped at 4")
    p.add_argument("--quality", default=None)
    p.add_argument("--response-format", default=None)
    p.add_argument("--mask", default=None, help="optional local mask image path")
    p.add_argument("--out", default="/root/.openclaw/media/qqbot/outputs")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--notify-feishu", default=None, help="open_id to auto-send image via Feishu native API after edit")
    p.add_argument("--no-notify", action="store_true", help="disable auto-send to Feishu even if FEISHU_NOTIFY_OPEN_ID is set")
    p.set_defaults(func=edit_image)


    p = sub.add_parser("enqueue", help="enqueue async image task (returns task id, image arrives later)")
    p.add_argument("--prompt", required=True)
    p.add_argument("--sender-id", default=None, help="QQ openId / Discord user id / target identifier")
    p.add_argument("--channel", default="qqbot", help="channel name: qqbot | discord | feishu | ...")
    p.add_argument("--type", default="c2c", choices=["c2c", "group", "channel", "user"])
    p.add_argument("--target", default=None, help="explicit target string; overrides sender-id+type")
    p.add_argument("--n", type=int, default=1, help="number of images, capped at 4")
    p.add_argument("--request-id", default=None)
    p.add_argument("--session-id", default=None, dest='session_id', help="source session id for context fork")
    p.add_argument("--queue", default=None, help="override queue file path")
    p.set_defaults(func=enqueue)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

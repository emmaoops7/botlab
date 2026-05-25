#!/usr/bin/env python3
"""Rewrite image prompts for Xdclaw async image jobs.

Keeps prompt improvement outside the main session. It is intentionally conservative:
- low: mostly preserve user wording; add only technical quality constraints
- medium: enrich composition/style while preserving all user-specified facts
- high: stronger creative completion for underspecified users

Config (optional, in openclaw.json):
{
  "channels": {"qqbot": {"imagePromptRewrite": {
    "default": "medium",
    "model": "mimo-v2.5-pro",
    "provider": "xdclaw-pool",
    "users": {"QQ_OPENID": "high"}
  }}}
}
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_CONFIGS = [
    "/root/.openclaw/openclaw.json",
    "/root/clawd/.openclaw/openclaw.json",
    os.path.expanduser("~/.openclaw/openclaw.json"),
]

LEVELS = {"off", "none", "low", "medium", "high"}


def load_config() -> dict[str, Any]:
    for p in DEFAULT_CONFIGS:
        try:
            return json.loads(Path(p).read_text())
        except Exception:
            continue
    return {}


def rewrite_config(cfg: dict[str, Any]) -> dict[str, Any]:
    return (((cfg.get("channels") or {}).get("qqbot") or {}).get("imagePromptRewrite") or {})


def pick_level(cfg: dict[str, Any], user: str, prompt: str, explicit: str | None) -> str:
    rc = rewrite_config(cfg)
    if explicit:
        level = explicit.lower()
    else:
        users = rc.get("users") or {}
        level = str(users.get(user) or rc.get("default") or "medium").lower()

    # Request-level overrides. User intent beats profile.
    if re.search(r"(严格按我说的|不要改|别改|原样|照我说的|不要自由发挥|不用改|别润色|不要润色|直接画)", prompt):
        level = "off"
    elif re.search(r"(帮我优化|帮我润色|你自由发挥|高级一点|更专业|效果好一点|大片|电影感)", prompt):
        level = "high"

    return level if level in LEVELS else "medium"


def provider_config(cfg: dict[str, Any], provider: str) -> tuple[str, str]:
    prov = (((cfg.get("models") or {}).get("providers") or {}).get(provider) or {})
    base = prov.get("baseUrl") or prov.get("base_url")
    key = prov.get("apiKey") or prov.get("api_key")
    if not base or not key:
        raise RuntimeError(f"provider {provider} missing baseUrl/apiKey")
    return str(base).rstrip("/"), str(key)


def call_llm(base: str, key: str, model: str, system: str, user: str, timeout: int) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.35,
        "max_tokens": 900,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", "ignore"))
    msg = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return clean_output(msg)


def clean_output(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:text|prompt)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"^(改写后提示词|提示词|Prompt)[:：]\s*", "", text.strip(), flags=re.I)
    return text.strip().strip('"')


def fallback_rewrite(prompt: str, level: str, kind: str) -> str:
    p = prompt.strip()
    if level in ("off", "none"):
        return p
    suffix_low = "，高清，避免畸形、文字乱码"
    suffix_medium = "，高质量商业摄影/插画级效果，主体清晰，构图自然，光线协调，细节丰富，质感真实，避免畸形、比例错误、文字乱码、低清晰度"
    suffix_high = "，完整场景设计，高级审美，主体突出，构图有层次，光线自然有氛围，材质和细节丰富，画面干净，专业成片质感，避免畸形、比例错误、多余肢体、文字乱码、低清晰度"
    suffix = {"low": suffix_low, "medium": suffix_medium, "high": suffix_high}.get(level, suffix_medium)
    if suffix in p:
        return p
    return p + suffix


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--kind", default="generate", choices=["generate", "edit"])
    ap.add_argument("--user", default="")
    ap.add_argument("--level", default=None)
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args()

    cfg = load_config()
    rc = rewrite_config(cfg)
    level = pick_level(cfg, args.user, args.prompt, args.level)
    original = args.prompt.strip()
    if level in ("off", "none") or not original:
        print(original)
        return

    provider = str(rc.get("provider") or "xdclaw-pool")
    model = str(rc.get("model") or "qwen3.6-plus")

    system = f"""你是图片生成 prompt rewrite 模块。只输出最终 prompt，不要解释。
目标：提升生图/图生图效果，但严格保留用户指定的主体、人物数量、身份、动作、文字、风格和禁忌。
当前 rewrite 级别：{level}。
- low: 不改动用户原文措辞和内容，只在末尾追加简短的质量约束和负面提示词。绝对不新增主体、风格、场景、构图描述。
- medium: 在不改变事实的前提下补充构图、光线、材质、镜头、质量词。
- high: 用户描述不足时可补充合理场景细节和审美方向，但不得改变核心需求。
图生图/edit 时尤其注意：保留原图主体身份、面部特征、人物数量和关键构图，不要大幅改人。
输出语言跟随用户原 prompt；如果中文更自然就中文。
"""
    user = f"任务类型：{args.kind}\n用户原始需求：{original}\n\n请输出改写后的图片生成 prompt："

    try:
        base, key = provider_config(cfg, provider)
        rewritten = call_llm(base, key, model, system, user, args.timeout)
        if not rewritten or len(rewritten) < max(6, len(original) // 4):
            raise RuntimeError("rewrite output too short")
        print(rewritten)
    except Exception as e:
        # Never fail the image job just because rewrite failed.
        print(fallback_rewrite(original, level, args.kind))
        print(f"[rewrite fallback: {e}]", file=sys.stderr)


if __name__ == "__main__":
    main()

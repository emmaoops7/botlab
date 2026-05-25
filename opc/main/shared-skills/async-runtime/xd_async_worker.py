#!/usr/bin/env python3
"""Async task worker for Xdclaw containers.
Claims one pending task, runs it via OpenClaw agent CLI, then completes/fails.
Delivers outbox messages via OpenClaw message send.
Designed to be called periodically by cron (every 15-30s).
"""
from __future__ import annotations
import json, subprocess, sys, time, os
from pathlib import Path

RUNTIME = Path('/root/clawd/shared-skills/async-runtime/xd_container_async_runtime.py')
FALLBACK_RUNTIME = Path('/opt/async-runtime/xd_container_async_runtime.py')
DB = os.environ.get('XDCLAW_CONTAINER_ASYNC_DB', '/root/.openclaw/async-runtime/tasks.sqlite3')
WORKER_ID = f'worker-{os.getpid()}'
LEASE_MS = 1_200_000  # 20 min
TASK_TIMEOUT = 900  # 15 min max per task
LOG = Path('/root/.openclaw/async-runtime/worker.log')

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}\n'
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, 'a') as f:
            f.write(line)
    except Exception:
        pass
    print(line, end='', file=sys.stderr)

def runtime_path():
    if RUNTIME.exists():
        return str(RUNTIME)
    if FALLBACK_RUNTIME.exists():
        return str(FALLBACK_RUNTIME)
    raise FileNotFoundError('async runtime not found')

def call_runtime(cmd_args):
    cmd = ['python3', runtime_path(), '--db', DB] + cmd_args
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        log(f'runtime error: {p.stderr[:500]}')
        return None
    try:
        return json.loads(p.stdout)
    except Exception:
        log(f'runtime parse error: {p.stdout[:500]}')
        return None

def run_task_via_openclaw(payload: dict) -> dict:
    """Run task prompt via openclaw agent CLI, return result dict."""
    prompt = payload.get('prompt', '')
    output_path = payload.get('output_path', '')
    if not prompt:
        return {'ok': False, 'error': 'empty prompt'}

    timeout = int(payload.get('timeout', TASK_TIMEOUT))
    cmd = [
        'openclaw', 'agent',
        '--json',
        '--message', prompt,
        '--agent', 'main',
        '--timeout', str(timeout),
    ]

    log(f'running openclaw agent: prompt={prompt[:100]}... timeout={timeout}')
    try:
        p = subprocess.run(cmd, cwd='/root/clawd', capture_output=True, text=True, timeout=timeout + 30)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'openclaw agent timed out'}

    if p.returncode != 0:
        return {'ok': False, 'error': f'openclaw exit {p.returncode}: {p.stderr[:300]}'}

    # Extract text from openclaw JSON output
    # openclaw agent --json may mix stderr into stdout on some containers
    # Filter out non-JSON lines, then try to parse
    raw = p.stdout.strip()
    # If there are non-JSON lines (like [plugins] logs), extract the JSON block
    if not raw.startswith('{'):
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start >= 0 and end > start:
            raw = raw[start:end]
    try:
        obj = json.loads(raw)
        text_parts = []
        # Standard path: result.payloads[].text
        if isinstance(obj.get('result'), dict):
            for pl in obj['result'].get('payloads', []):
                if pl.get('text'):
                    text_parts.append(pl['text'])
        # Fallback: top-level payloads
        if not text_parts and obj.get('payloads'):
            for pl in obj['payloads']:
                if pl.get('text'):
                    text_parts.append(pl['text'])
        # Fallback: top-level text
        if not text_parts and obj.get('text'):
            text_parts.append(obj['text'])
        text = '\n'.join(text_parts).strip()
        if not text:
            text = '任务已完成（无文本输出）'
    except json.JSONDecodeError:
        # Last resort: find the text field in raw output
        import re
        m = re.search(r'"text"\s*:\s*"([^"]+)"', raw)
        text = m.group(1) if m else '任务已完成（无文本输出）'
    except Exception:
        text = '任务已完成'

    # If output_path specified, also save to file
    if output_path:
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(text)
            log(f'saved result to {output_path}')
        except Exception as e:
            log(f'failed to save result: {e}')

    return {'ok': True, 'text': text}

def deliver_outbox():
    """Deliver pending outbox messages via openclaw message send."""
    result = call_runtime(['outbox', '--limit', '5'])
    if not result or not result.get('ok'):
        return
    items = result.get('items', [])
    for item in items:
        mid = item['id']
        channel = item.get('channel', 'qqbot')
        target = item.get('target', '')
        text = item.get('text', '')
        if not text or not target:
            log(f'outbox {mid}: skip (no text or target)')
            call_runtime(['mark-delivered', mid, '--delivery-ref', 'skipped'])
            continue

        log(f'delivering outbox {mid} to {channel}:{target}: {text[:80]}...')
        try:
            cmd = ['openclaw', 'message', 'send',
                   '-t', target,
                   '--channel', channel,
                   '-m', text[:1800]]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if p.returncode == 0:
                call_runtime(['mark-delivered', mid, '--delivery-ref', f'sent:{p.stdout.strip()[:100]}'])
                log(f'outbox {mid}: delivered')
            else:
                log(f'outbox {mid}: send failed: {p.stderr[:200]}')
        except Exception as e:
            log(f'outbox {mid}: exception: {e}')

def main():
    log('=== async worker tick start ===')

    # 1. Reap expired leases
    call_runtime(['reap'])

    # 2. Claim one task
    result = call_runtime(['claim', '--worker-id', WORKER_ID, '--lease-ms', str(LEASE_MS)])
    if not result or not result.get('ok'):
        log('claim failed or runtime error')
        deliver_outbox()
        return

    task = result.get('task')
    if not task:
        log('no pending tasks')
        deliver_outbox()
        return

    task_id = task['id']
    payload = task.get('payload', {})
    task_type = task.get('type', 'unknown')
    channel = None
    target = None

    # Get channel/target from interaction
    ix_id = task.get('interaction_id')

    log(f'claimed task {task_id} type={task_type}')

    # 3. Execute task
    try:
        result = run_task_via_openclaw(payload)
        if result.get('ok'):
            call_runtime(['complete', task_id,
                          '--result', json.dumps(result, ensure_ascii=False),
                          '--emit-message'])
            log(f'task {task_id}: completed')
        else:
            call_runtime(['fail', task_id,
                          '--error', result.get('error', 'unknown error'),
                          '--emit-message'])
            log(f'task {task_id}: failed: {result.get("error")}')
    except Exception as e:
        call_runtime(['fail', task_id, '--error', str(e), '--emit-message'])
        log(f'task {task_id}: exception: {e}')

    # 4. Deliver outbox
    deliver_outbox()
    log('=== async worker tick end ===')

if __name__ == '__main__':
    main()

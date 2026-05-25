#!/usr/bin/env python3
import json, os, time, shutil
from pathlib import Path

ROOT = Path('/root/clawd/workspace') if Path('/root/clawd/workspace').exists() else Path('/root/clawd')
MEM = ROOT / 'memory'
STATE = MEM / '_state.json'
INDEX = MEM / 'index.md'
NOW = int(time.time())
DAY = 86400
TODO_STALE_DAYS = 30
DONE_KEEP_DAYS = 7
KNOWLEDGE_STALE_DAYS = 100
CONV_CHECK_DAYS = 14
CONV_DELETE_DAYS = 30
ARCHIVE = MEM / '.archive'
ARCHIVE.mkdir(parents=True, exist_ok=True)


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_state(data):
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def ts(path):
    try:
        return int(path.stat().st_mtime)
    except Exception:
        return NOW


def ensure_entry(state, rel, critical=False):
    e = state.setdefault(rel, {})
    e.setdefault('createdAt', ts(MEM / rel.replace('memory/','')) if rel.startswith('memory/') else NOW)
    e.setdefault('updatedAt', ts(MEM / rel.replace('memory/','')) if rel.startswith('memory/') else NOW)
    e.setdefault('lastReferenced', 0)
    e.setdefault('referenceCount', 0)
    e.setdefault('critical', critical)
    return e


def clean_todo(path):
    if not path.exists():
        return False
    lines = path.read_text(encoding='utf-8').splitlines()
    new=[]
    current=''
    changed=False
    for line in lines:
        s=line.strip()
        if s.startswith('## '):
            current=s
            new.append(line)
            continue
        if s.startswith('- ['):
            # simple age rule via file mtime only; old completed/todo blocks get reset by user edits
            age_days=(NOW-ts(path))//DAY
            if current=='## 已完成' and age_days > DONE_KEEP_DAYS:
                changed=True
                continue
            if current in ('## 待办','## 待提醒') and age_days > TODO_STALE_DAYS:
                changed=True
                continue
        new.append(line)
    if changed:
        path.write_text('\n'.join(new).rstrip()+'\n', encoding='utf-8')
    return changed


def handle_knowledge(state):
    changed=False
    for p in sorted((MEM/'knowledge').glob('*.md')):
        rel=f'memory/knowledge/{p.name}'
        e=ensure_entry(state, rel)
        age=(NOW-int(e.get('lastReferenced') or 0))//DAY if e.get('lastReferenced') else (NOW-ts(p))//DAY
        if age >= KNOWLEDGE_STALE_DAYS:
            if e.get('critical'):
                dst=ARCHIVE/p.name
                shutil.move(str(p), str(dst))
            else:
                p.unlink(missing_ok=True)
            state.pop(rel, None)
            changed=True
    return changed


def handle_conversations(state):
    changed=False
    for p in sorted((MEM/'conversations').glob('*.md')):
        rel=f'memory/conversations/{p.name}'
        e=ensure_entry(state, rel)
        age_ref=(NOW-int(e.get('lastReferenced') or 0))//DAY if e.get('lastReferenced') else 9999
        age_file=(NOW-ts(p))//DAY
        if age_file >= CONV_DELETE_DAYS and age_ref >= CONV_DELETE_DAYS:
            p.unlink(missing_ok=True)
            state.pop(rel, None)
            changed=True
    return changed


def rebuild_index():
    lines=[
        '# 知识索引','',
        '| 文件 | 内容 |','|------|------|',
        '| `memory/core.md` | 长期稳定事实、明确偏好、红线、长期目标 |',
        '| `memory/记事本.md` | 待办、提醒、临时事项、已完成事项 |',
        '', '## knowledge'
    ]
    ks=sorted((MEM/'knowledge').glob('*.md'))
    if ks:
        for p in ks:
            lines.append(f'- [{p.stem}](knowledge/{p.name})')
    else:
        lines.append('（待补充）')
    lines += ['', '## conversations']
    cs=sorted((MEM/'conversations').glob('*.md'))
    if cs:
        for p in cs:
            lines.append(f'- [{p.stem}](conversations/{p.name})')
    else:
        lines.append('（待补充）')
    INDEX.write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    MEM.mkdir(parents=True, exist_ok=True)
    (MEM/'knowledge').mkdir(exist_ok=True)
    (MEM/'conversations').mkdir(exist_ok=True)
    state=load_state()
    for p in (MEM/'knowledge').glob('*.md'):
        ensure_entry(state, f'memory/knowledge/{p.name}')
    for p in (MEM/'conversations').glob('*.md'):
        ensure_entry(state, f'memory/conversations/{p.name}')
    clean_todo(MEM/'记事本.md')
    handle_knowledge(state)
    handle_conversations(state)
    rebuild_index()
    save_state(state)
    print('OK: memory maintenance done')

if __name__ == '__main__':
    main()

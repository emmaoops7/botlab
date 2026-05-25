#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from pathlib import Path
BASE=Path('/root/.openclaw/async-runtime')
def call(cmd,timeout=120):
    p=subprocess.run(['python3',str(cmd[0]),*cmd[1:]],capture_output=True,text=True,timeout=timeout)
    data=None
    try: data=json.loads(p.stdout) if p.stdout.strip() else None
    except Exception: data={'raw':p.stdout[-1000:]}
    return {'cmd':[str(x) for x in cmd],'rc':p.returncode,'data':data,'stderr':p.stderr[-1000:]}
def main():
    steps=[]
    steps.append(call([BASE/'xd_container_async_runtime.py','reap']))
    steps.append(call([BASE/'xd_container_image_worker.py','work','--limit','1'],timeout=900))
    steps.append(call([BASE/'xd_container_async_runtime.py','status']))
    print(json.dumps({'ok':all(x['rc']==0 for x in steps),'steps':steps},ensure_ascii=False))
if __name__=='__main__': main()

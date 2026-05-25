#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path
RUNTIME=Path('/root/.openclaw/async-runtime/xd_container_async_runtime.py')
DEFAULT_SCRIPT='/root/clawd/skills/multimodal-image/scripts/mm_image.py'
OUT='/root/.openclaw/media/qqbot/outputs'
DEFAULT_FEISHU_OPEN_ID='ou_5cc59c09e86ae9f0e57effc77f9fdd38'

SUPPORTED={'image.generate','image.edit','image.understand'}

def rt(args):
    p=subprocess.run(['python3',str(RUNTIME),*args],capture_output=True,text=True,timeout=60)
    if p.returncode!=0: raise RuntimeError(p.stderr or p.stdout)
    return json.loads(p.stdout)

def _payload_target(payload):
    return str(payload.get('target') or payload.get('senderId') or '').strip()

def _feishu_open_id(ch, payload):
    if ch != 'feishu':
        return None
    explicit = payload.get('feishuOpenId') or payload.get('notify_feishu') or payload.get('notifyFeishu')
    if explicit:
        return str(explicit).strip()
    target = _payload_target(payload)
    if target.startswith('direct:'):
        target = target.split(':',1)[1]
    if target.startswith('ou_'):
        return target
    return DEFAULT_FEISHU_OPEN_ID

def build(t,payload,ch=None):
    if t not in SUPPORTED: raise ValueError('unsupported type '+str(t))
    prompt=(payload.get('prompt') or payload.get('text') or '').strip()
    if not prompt: raise ValueError('missing prompt')
    script=payload.get('script') or DEFAULT_SCRIPT
    if t == 'image.understand':
        imgs=payload.get('images') or payload.get('image') or []
        if isinstance(imgs,str): imgs=[imgs]
        if not imgs: raise ValueError('missing image(s)')
        cmd=['python3',script,'understand']
        for img in imgs[:4]: cmd += ['--image',str(img)]
        cmd += ['--prompt',prompt]
        for k,opt in [('model','--model'),('provider','--provider'),('timeout','--timeout')]:
            if payload.get(k) is not None: cmd += [opt,str(payload[k])]
        return cmd,prompt
    if t == 'image.edit':
        imgs=payload.get('images') or payload.get('image') or []
        if isinstance(imgs,str): imgs=[imgs]
        if not imgs: raise ValueError('missing image(s)')
        cmd=['python3',script,'edit']
        for img in imgs[:4]: cmd += ['--image',str(img)]
        cmd += ['--prompt',prompt,'--out',payload.get('out') or OUT]
        if payload.get('mask'): cmd += ['--mask',str(payload['mask'])]
    else:
        cmd=['python3',script,'generate','--prompt',prompt,'--out',payload.get('out') or OUT]
        if payload.get('n') is not None: cmd += ['--n',str(payload['n'])]
    for k,opt in [('model','--model'),('provider','--provider'),('size','--size'),('quality','--quality'),('timeout','--timeout')]:
        if payload.get(k) is not None: cmd += [opt,str(payload[k])]
    notify=_feishu_open_id(ch,payload)
    if notify:
        cmd += ['--notify-feishu',notify]
    elif payload.get('no_notify') or payload.get('noNotify') or ch != 'feishu':
        # Avoid sending QQ-originated lab images to the hard-coded Feishu default.
        cmd += ['--no-notify']
    return cmd,prompt

def notify_user(ch, tg, msg):
    if ch and tg:
        import subprocess as _sp
        try:
            _sp.run(['openclaw','agent','--agent','main','--deliver','--reply-channel',ch,'--reply-to',tg,'--message',msg],
                    capture_output=True, timeout=10)
        except Exception:
            pass

def work(args):
    done=[]
    for _ in range(args.limit):
        d=rt(['claim','--worker-id',args.worker_id,'--lease-ms',str(args.lease_ms)])
        task=d.get('task')
        if not task: break
        if task.get('type') not in SUPPORTED:
            rt(['fail',task['id'],'--error','unsupported type '+str(task.get('type')),'--emit-message'])
            continue
        tid=task['id']; iid=task.get('interaction_id',''); ch,tg=None,None
        if iid:
            ixr=rt(['interaction',iid]); ix=ixr.get('interaction')
            if ix: ch,tg=ix.get('channel'),ix.get('target')
        if task.get('type') != 'image.understand':
            notify_user(ch,tg,f'✨ 任务 {tid[:8]} 开始生成，请稍候...')
        try:
            payload=task.get('payload') or {}
            cmd,prompt=build(task['type'],payload,ch)
            p=subprocess.run(cmd,cwd='/root/clawd',capture_output=True,text=True,timeout=args.timeout)
            if p.returncode!=0:
                r=rt(['fail',task['id'],'--error',(p.stderr or p.stdout or 'image worker failed')[-2000:],'--emit-message'])
                notify_user(ch,tg,'❌ 生成失败: '+str(r.get('error','未知错误'))[:200])
            else:
                lines=[x.strip() for x in p.stdout.splitlines() if x.strip()]
                paths=[x for x in lines if x.startswith('/')]
                if task.get('type') == 'image.understand':
                    text='\n'.join(lines) or '已完成图片理解'
                else:
                    text='图片已生成：\n'+'\n'.join(f'<qqmedia>{x}</qqmedia>' for x in paths) if paths else (p.stdout.strip() or '图片已生成')
                r=rt(['complete',task['id'],'--result',json.dumps({'text':text,'paths':paths,'prompt':prompt},ensure_ascii=False),'--emit-message'])
                # Feishu image native API already sends the actual image. Send only short completion text to avoid broken local-path media fallback.
                if ch == 'feishu' and paths and task.get('type') != 'image.understand':
                    notify_user(ch,tg,'✅ 图片已生成并自动发送。')
                else:
                    notify_user(ch,tg,text)
            done.append(r)
        except Exception as e:
            done.append(rt(['fail',task['id'],'--error',f'{type(e).__name__}: {e}','--emit-message']))
            notify_user(ch,tg,f'❌ 执行异常: {type(e).__name__}: {e}')
    print(json.dumps({'ok':True,'count':len(done),'results':done},ensure_ascii=False))

def enqueue(args):
    payload={'prompt':args.prompt,'model':args.model,'provider':args.provider,'size':args.size,'n':args.n,'timeout':args.timeout}
    payload={k:v for k,v in payload.items() if v not in (None,'')}
    cmd=['enqueue','--type','image.generate','--payload',json.dumps(payload,ensure_ascii=False)]
    for opt,val in [('--interaction-id',args.interaction_id),('--owner',args.owner),('--channel',args.channel),('--target',args.target),('--message-plan',args.message_plan)]:
        if val: cmd += [opt,val]
    print(json.dumps(rt(cmd),ensure_ascii=False))

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('enqueue'); s.add_argument('--prompt',required=True); s.add_argument('--interaction-id'); s.add_argument('--owner'); s.add_argument('--channel'); s.add_argument('--target'); s.add_argument('--message-plan',default='{}'); s.add_argument('--model'); s.add_argument('--provider'); s.add_argument('--size'); s.add_argument('--n',type=int); s.add_argument('--timeout',type=int); s.set_defaults(func=enqueue)
    s=sub.add_parser('work'); s.add_argument('--limit',type=int,default=1); s.add_argument('--timeout',type=int,default=600); s.add_argument('--worker-id',default='image-worker'); s.add_argument('--lease-ms',type=int,default=900000); s.set_defaults(func=work)
    args=ap.parse_args(); args.func(args)
if __name__=='__main__': main()

#!/usr/bin/env python3
"""Per-container Xdclaw async runtime.
Durable sqlite queue kept inside each user container. No host/session state required.
"""
from __future__ import annotations
import argparse, json, os, sqlite3, time, uuid
from pathlib import Path

DEFAULT_DB = Path(os.environ.get('XDCLAW_CONTAINER_ASYNC_DB', '/root/.openclaw/async-runtime/tasks.sqlite3'))
TERMINAL = {'succeeded','failed','timed_out','cancelled'}

def now_ms(): return int(time.time()*1000)
def nid(p): return f'{p}_{uuid.uuid4().hex[:16]}'
def jloads(s, default=None):
    if not s: return default
    try: return json.loads(s)
    except Exception: return default

def db(path=DEFAULT_DB):
    path.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(str(path), timeout=30, isolation_level=None)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA busy_timeout=30000')
    return c

def init(c):
    c.executescript('''
CREATE TABLE IF NOT EXISTS interactions(
 id TEXT PRIMARY KEY, owner TEXT, channel TEXT, target TEXT, session_key TEXT,
 status TEXT NOT NULL DEFAULT 'open', message_plan_json TEXT NOT NULL DEFAULT '{}',
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, closed_at INTEGER
);
CREATE TABLE IF NOT EXISTS tasks(
 id TEXT PRIMARY KEY, interaction_id TEXT, type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
 priority INTEGER NOT NULL DEFAULT 100, payload_json TEXT NOT NULL DEFAULT '{}', result_json TEXT, error TEXT,
 attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 1,
 run_after INTEGER NOT NULL DEFAULT 0, lease_until INTEGER NOT NULL DEFAULT 0, worker_id TEXT,
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, started_at INTEGER, finished_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_tasks_ready ON tasks(status, run_after, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_ix ON tasks(interaction_id,status);
CREATE TABLE IF NOT EXISTS outbox(
 id TEXT PRIMARY KEY, interaction_id TEXT, task_id TEXT, channel TEXT, target TEXT,
 text TEXT NOT NULL, media_json TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'pending',
 created_at INTEGER NOT NULL, delivered_at INTEGER, delivery_ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status,created_at);
''')

def ensure_ix(c,args):
    iid=args.interaction_id or nid('ix')
    t=now_ms()
    row=c.execute('SELECT id FROM interactions WHERE id=?',(iid,)).fetchone()
    if not row:
        c.execute('INSERT INTO interactions(id,owner,channel,target,session_key,message_plan_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                  (iid,args.owner,args.channel,args.target,args.session_key,args.message_plan,t,t))
    return iid

def cmd_init(args):
    c=db(Path(args.db)); init(c)
    print(json.dumps({'ok':True,'db':args.db},ensure_ascii=False))

def cmd_enqueue(args):
    c=db(Path(args.db)); init(c); t=now_ms(); iid=ensure_ix(c,args); tid=args.task_id or nid('task')
    c.execute('INSERT INTO tasks(id,interaction_id,type,status,priority,payload_json,max_attempts,run_after,created_at,updated_at) VALUES(?,?,?,\'pending\',?,?,?,?,?,?)',
              (tid,iid,args.type,args.priority,args.payload,args.max_attempts,t+args.delay_ms,t,t))
    print(json.dumps({'ok':True,'interaction_id':iid,'task_id':tid},ensure_ascii=False))

def cmd_claim(args):
    c=db(Path(args.db)); init(c); t=now_ms(); lease=t+args.lease_ms
    c.execute('BEGIN IMMEDIATE')
    where=['status=\'pending\'','run_after<=?']; params=[t]
    if args.type: where.append('type=?'); params.append(args.type)
    row=c.execute(f"SELECT * FROM tasks WHERE {' AND '.join(where)} ORDER BY priority,created_at LIMIT 1", tuple(params)).fetchone()
    if not row:
        c.execute('COMMIT'); print(json.dumps({'ok':True,'task':None},ensure_ascii=False)); return
    c.execute('UPDATE tasks SET status=\'running\', attempts=attempts+1, worker_id=?, lease_until=?, started_at=COALESCE(started_at,?), updated_at=? WHERE id=?',
              (args.worker_id,lease,t,t,row['id']))
    c.execute('COMMIT')
    d=dict(row); d['status']='running'; d['payload']=jloads(d.pop('payload_json'),{})
    print(json.dumps({'ok':True,'task':d},ensure_ascii=False))

def result_text(res):
    if isinstance(res,dict): return str(res.get('text') or res.get('summary') or res.get('error') or json.dumps(res,ensure_ascii=False))
    return str(res)

def cmd_complete(args):
    c=db(Path(args.db)); init(c); t=now_ms(); res=jloads(args.result,{})
    row=c.execute('SELECT * FROM tasks WHERE id=?',(args.task_id,)).fetchone()
    if not row: print(json.dumps({'ok':False,'error':'task not found'},ensure_ascii=False)); return
    c.execute('UPDATE tasks SET status=\'succeeded\', result_json=?, error=NULL, lease_until=0, updated_at=?, finished_at=? WHERE id=?', (args.result,t,t,args.task_id))
    ix=c.execute('SELECT * FROM interactions WHERE id=?',(row['interaction_id'],)).fetchone()
    if args.emit_message:
        oid=nid('msg'); text=result_text(res); media=res.get('paths') if isinstance(res,dict) else []
        c.execute('INSERT INTO outbox(id,interaction_id,task_id,channel,target,text,media_json,status,created_at) VALUES(?,?,?,?,?,?,?,\'pending\',?)',
                  (oid,row['interaction_id'],args.task_id, args.channel or (ix['channel'] if ix else None), args.target or (ix['target'] if ix else None), text, json.dumps(media or [],ensure_ascii=False), t))
    print(json.dumps({'ok':True,'task_id':args.task_id},ensure_ascii=False))

def cmd_fail(args):
    c=db(Path(args.db)); init(c); t=now_ms()
    row=c.execute('SELECT * FROM tasks WHERE id=?',(args.task_id,)).fetchone()
    if not row: print(json.dumps({'ok':False,'error':'task not found'},ensure_ascii=False)); return
    status='failed'; run_after=0; finished=t
    if row['attempts'] < row['max_attempts']:
        status='pending'; run_after=t+args.retry_delay_ms; finished=None
    c.execute('UPDATE tasks SET status=?, error=?, lease_until=0, run_after=?, updated_at=?, finished_at=? WHERE id=?', (status,args.error,run_after,t,finished,args.task_id))
    if status=='failed' and args.emit_message:
        ix=c.execute('SELECT * FROM interactions WHERE id=?',(row['interaction_id'],)).fetchone(); oid=nid('msg')
        c.execute('INSERT INTO outbox(id,interaction_id,task_id,channel,target,text,status,created_at) VALUES(?,?,?,?,?,?,\'pending\',?)',
                  (oid,row['interaction_id'],args.task_id,args.channel or (ix['channel'] if ix else None),args.target or (ix['target'] if ix else None),'有一个任务失败：'+args.error,t))
    print(json.dumps({'ok':True,'task_id':args.task_id,'status':status},ensure_ascii=False))

def cmd_reap(args):
    c=db(Path(args.db)); init(c); t=now_ms(); rows=c.execute("SELECT * FROM tasks WHERE status='running' AND lease_until>0 AND lease_until<?",(t,)).fetchall(); n=0
    for r in rows:
        c.execute("UPDATE tasks SET status='pending', lease_until=0, worker_id=NULL, updated_at=? WHERE id=?",(t,r['id'])); n+=1
    print(json.dumps({'ok':True,'reaped':n},ensure_ascii=False))

def cmd_outbox(args):
    c=db(Path(args.db)); init(c)
    rows=c.execute("SELECT * FROM outbox WHERE status='pending' ORDER BY created_at LIMIT ?",(args.limit,)).fetchall()
    print(json.dumps({'ok':True,'items':[dict(r) for r in rows]},ensure_ascii=False))

def cmd_mark_delivered(args):
    c=db(Path(args.db)); init(c); t=now_ms()
    for mid in args.ids:
        c.execute("UPDATE outbox SET status='delivered', delivered_at=?, delivery_ref=? WHERE id=?",(t,args.delivery_ref,mid))
    print(json.dumps({'ok':True,'count':len(args.ids)},ensure_ascii=False))

def cmd_status(args):
    c=db(Path(args.db)); init(c)
    rows=c.execute('SELECT status, COUNT(*) n FROM tasks GROUP BY status').fetchall()
    out=c.execute('SELECT status, COUNT(*) n FROM outbox GROUP BY status').fetchall()
    print(json.dumps({'ok':True,'tasks':{r['status']:r['n'] for r in rows},'outbox':{r['status']:r['n'] for r in out}},ensure_ascii=False))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--db',default=str(DEFAULT_DB)); sub=ap.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('init'); s.set_defaults(func=cmd_init)
    s=sub.add_parser('enqueue'); s.add_argument('--type',required=True); s.add_argument('--payload',default='{}'); s.add_argument('--task-id'); s.add_argument('--interaction-id'); s.add_argument('--owner'); s.add_argument('--channel'); s.add_argument('--target'); s.add_argument('--session-key'); s.add_argument('--message-plan',default='{}'); s.add_argument('--priority',type=int,default=100); s.add_argument('--delay-ms',type=int,default=0); s.add_argument('--max-attempts',type=int,default=1); s.set_defaults(func=cmd_enqueue)
    s=sub.add_parser('claim'); s.add_argument('--type'); s.add_argument('--worker-id',default='worker'); s.add_argument('--lease-ms',type=int,default=900000); s.set_defaults(func=cmd_claim)
    s=sub.add_parser('complete'); s.add_argument('task_id'); s.add_argument('--result',required=True); s.add_argument('--emit-message',action='store_true'); s.add_argument('--channel'); s.add_argument('--target'); s.set_defaults(func=cmd_complete)
    s=sub.add_parser('fail'); s.add_argument('task_id'); s.add_argument('--error',required=True); s.add_argument('--retry-delay-ms',type=int,default=30000); s.add_argument('--emit-message',action='store_true'); s.add_argument('--channel'); s.add_argument('--target'); s.set_defaults(func=cmd_fail)
    s=sub.add_parser('reap'); s.set_defaults(func=cmd_reap)
    s=sub.add_parser('outbox'); s.add_argument('--limit',type=int,default=20); s.set_defaults(func=cmd_outbox)
    s=sub.add_parser('mark-delivered'); s.add_argument('ids',nargs='+'); s.add_argument('--delivery-ref',default='manual'); s.set_defaults(func=cmd_mark_delivered)
    s=sub.add_parser('status'); s.set_defaults(func=cmd_status)
    args=ap.parse_args(); args.func(args)
if __name__=='__main__': main()

"""Explicit owned-lab mode switch, preserving data and previous configuration."""
import argparse
import json
import pathlib
import sqlite3
from engine_hub.scripts.lab import stop,LOCAL,ROOT


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['fixture','luna']);a=p.parse_args()
    db=LOCAL/'manager.db'
    if db.exists():
        with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as c:
            rows=[json.loads(x[0]) for x in c.execute("SELECT data FROM records WHERE kind='runs'")]
        if any(r['status'] not in ['completed','cancelled','failed','expired','interrupted'] for r in rows):
            raise RuntimeError('Reconcile active/uncertain Manager Runs before mode change')
    for name in ['ui','manager','node-03','node-03-state','luna-bridge']:stop(name)
    p=LOCAL/'config.json';cfg=json.loads(p.read_text());n=next(n for n in cfg['nodes'] if n['id']=='node-03')
    cfg['model_bridge']=a.mode=='luna'
    cfg['classifier']={'kind':'rules'} if a.mode=='fixture' else {'kind':'codex-luna','executable':'/home/ruby/.npm-global/bin/codex'}
    corefile=LOCAL/'nodes/node-03/home/config.yaml';core=json.loads(corefile.read_text())
    if a.mode=='luna':
        n['model']='codex-luna-bridge'
        core['model'].update({'default':'codex-luna-bridge','base_url':'http://127.0.0.1:15806/v1','api_key':n['key']})
    else:
        n.pop('model',None)
        core['model'].update({'default':'webui-node-fixture','base_url':'http://127.0.0.1:15803/v1','api_key':'local-fixture-only'})
    p.write_text(json.dumps(cfg,indent=2)+'\n');corefile.write_text(json.dumps(core));corefile.chmod(0o600)
    print('Owned mode changed to '+a.mode+'; no services started.')


if __name__=='__main__':main()

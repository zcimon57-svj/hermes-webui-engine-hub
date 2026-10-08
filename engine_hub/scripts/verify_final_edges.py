import json
import pathlib
import secrets
import time
from engine_hub.scripts import verify_live as v
from engine_hub.common import Store,canonical,digest
from engine_hub.manager import ManagerClient


def main():
    root=v.ROOT;s=json.loads((root/'.local/secrets.json').read_text())
    admin=v.Client('admin',s['passwords']['admin']);reviewer=v.Client('reviewer',s['passwords']['reviewer'])
    cfg=json.loads((root/'.local/config.json').read_text())
    source=next(r for r in json.loads((root/'.local/guarded-runs.json').read_text()) if r['engine']=='pg')
    base=admin.ok('/assets/pg/current')
    content='SYNTHETIC PG guarded publication '+secrets.token_hex(8)
    package={'SKILL.md':'---\nname: engine-ops\ndescription: PG synthetic approved method\n---\nSynthetic PG method; verify cited evidence.',
        'scripts/probe.py':'print("PG_GUARDED_APPROVED_SCRIPT")','references/method.md':'Synthetic read-only reference.',
        'dependencies.json':'{"python":"3.11","packages":{}}'}
    body={'source':{'run':source['id']},'base':base['id'],'knowledge':content,'package':package,'share_consent':True,'origin':'MANUAL_SYNTHETIC'}
    candidate=admin.ok('/assets/pg/candidates','POST',body)
    reviewer.ok('/assets/pg/candidates/'+candidate['id']+'/evaluate','POST',{'passed':True,'evidence':['FUNCTIONAL_ONLY']})
    release=reviewer.ok('/assets/pg/candidates/'+candidate['id']+'/approve','POST',{'base':base['id']})
    v.check('native_revision_pinned',all(isinstance(d.get('remote_revision'),int) for d in release['documents'].values()))
    readback=admin.ok('/assets/pg/releases/'+release['id'])
    v.check('remote_publish_readback',readback['content']['knowledge']['content']==content)
    request={'engine':'pg','text':'PG consume new version and test explicit idempotency','input_revision':secrets.token_hex(16)}
    admitted=admin.ok('/ask','POST',request)
    repeated=admin.ok('/ask','POST',request)
    v.check('UI_revision_idempotent',admitted['run']['id']==repeated['run']['id'] and admitted['conversation']['id']==repeated['conversation']['id'])
    run=v.terminal(admin,admitted['run']['id']);actual=v.identity(run['report'])
    v.check('new_run_consumes_published_revision',actual['release']==release['id'] and actual['knowledge']['content']==content and 'PG_GUARDED_APPROVED_SCRIPT' in actual['script_output'])
    admin.denied('/ask','POST',{**request,'text':'different body'},409)
    # Simulate a lost UI receipt: the business record stays in the Manager.
    store=Store(root/'.local/ui.db');ref=store.get('run_refs',run['id']);conversation=store.get('conversations',run['conversation'])
    with store.connect() as db:db.execute("DELETE FROM records WHERE kind='run_refs' AND id=?",(run['id'],))
    store.put('conversations',conversation['id'],{**conversation,'turns':[]})
    try:
        v.check('lost_UI_receipt_read_recovery',admin.ok('/runs/'+run['id'])['report_sha256']==run['report_sha256'])
        summary=admin.ok('/summary')
        v.check('lost_receipt_visible_in_normal_UI',any(r['id']==run['id'] for r in summary['runs']) and
            admin.ok('/conversations/'+conversation['id'])['turns'][0]['run']==run['id'])
        v.check('GET_recovery_does_not_autosave',store.get('conversations',conversation['id'])['turns']==[])
    finally:
        store.put('run_refs',run['id'],ref);store.put('conversations',conversation['id'],conversation)
    # Restricted project space is a real authenticated user; no fake headers.
    name='spacechat'+secrets.token_hex(4);password=secrets.token_urlsafe(20)
    admin.ok('/users','POST',{'name':name,'password':password,'role':'chat','engines':['pg'],'spaces':['pg-lab']})
    scoped=v.Client(name,password)
    scoped.denied('/route','POST',{'engine':'pg','instance':'pg-prod-test','text':'PG'},404)
    route=scoped.ok('/route','POST',{'instance':'pg-lab-test','text':'PG'})
    v.check('authorized_project_instance',route['space']=='pg-lab')
    scoped.denied('/runs/'+run['id'],status=404)
    scoped.denied('/runs/'+run['id']+'/events',status=404)
    scoped.denied('/runs/'+run['id']+'/download',status=404)
    reviewer.ok('/assets/pg/releases/'+release['id']+'/withdraw','POST',{'reason':'Controlled withdrawal'})
    admin.denied('/assets/pg/releases/'+release['id'],status=410)
    reviewer.ok('/assets/pg/rollback','POST',{'base':release['id'],'target':base['id']})
    v.check('reports_survive_withdrawal',admin.ok('/runs/'+run['id'])['report_sha256']==run['report_sha256'])


if __name__=='__main__':
    name='final-edges-'+str(time.time_ns())+'.json';status='PASS';error=None
    try:main()
    except Exception as e:status='FAIL';error=str(e);raise
    finally:
        (v.ROOT/'evidence'/name).write_text(json.dumps({'status':status,'error':error,'checks':v.CHECKS,'trace':v.TRACE,
            'boundary':'Actual HTTP identity, remote content/revisions, Gateway consumption, UI receipt recovery and project-space denial; synthetic fixture quality only'},indent=2)+'\n')
        print(json.dumps({'status':status,'checks':len(v.CHECKS),'evidence':name,'error':error}))

import json
import pathlib
import time
from engine_hub.codex_luna import CodexLuna
from engine_hub.resources import host_snapshot,require_containment

root=pathlib.Path(__file__).resolve().parents[1]
require_containment();before=host_snapshot()
model=CodexLuna(root/'.local/luna-guarded','/home/ruby/.npm-global/bin/codex')
result=model.classify('WAL replication slot inactive，日志保留导致磁盘占用增加，需要证据核对',['mysql','pg','cassandra','redis'])
after=host_snapshot()
evidence={'status':'PASS' if result['selected']=='pg' else 'FAIL','result':result,'before':before,'after':after,
    'boundary':'One actual authorized Luna inference under global model mutex, one-core affinity and shared 1 GiB envelope; not a domain-quality acceptance set'}
file=root/'evidence'/('luna-guarded-'+str(time.time_ns())+'.json');file.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':evidence['status'],'evidence':str(file),'selected':result['selected']}));assert evidence['status']=='PASS'

import json
import os
import pathlib
import subprocess
import threading
import time
from engine_hub.resources import ensure_slice,require_containment,host_snapshot,CPU,LOCAL,acquire_model_slot


def main():
    require_containment();p,limits=ensure_slice()
    before=host_snapshot();mask=[]
    workers=[threading.Thread(target=lambda:mask.append(sorted(os.sched_getaffinity(0)))) for _ in range(3)]
    for thread in workers:thread.start()
    for thread in workers:thread.join()
    lock=acquire_model_slot()
    code='from engine_hub.resources import acquire_model_slot; acquire_model_slot()'
    second=subprocess.run(['python3','-c',code],capture_output=True,text=True,timeout=10)
    lock.close()
    inherited=json.loads(subprocess.check_output(['python3','-c','import os,json;print(json.dumps(sorted(os.sched_getaffinity(0))))'],text=True))
    buffer=bytearray(16*1024**2);buffer[0]=1
    after=host_snapshot()
    result={'status':'PASS','kernel_limits':limits,'cgroup':str(p),'cpu_affinity':sorted(os.sched_getaffinity(0)),
        'thread_affinities':mask,'child_affinity':inherited,'global_model_second_denied':second.returncode!=0 and 'global_model_budget' in second.stderr,
        'before':before,'after':after,'boundary':'Actual inherited affinity, cgroup memory/pid controls and cross-process model mutex; no memory saturation or stress beyond 16 MiB.'}
    assert inherited==[CPU] and all(x==[CPU] for x in mask) and result['global_model_second_denied']
    dest=pathlib.Path(__file__).resolve().parents[1]/'evidence'/('resource-controls-'+str(time.time_ns())+'.json')
    dest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASS','evidence':str(dest)}))


if __name__=='__main__':main()

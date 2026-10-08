"""Run a bounded test/model/browser command inside the same hard lab envelope."""
import argparse
import json
import pathlib
import secrets
import subprocess
import sys
from engine_hub.resources import check_admission,scope_command,LOCAL,boot_id


def main():
    p=argparse.ArgumentParser();p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    cmd=a.command[1:] if a.command[:1]==['--'] else a.command
    if not cmd:raise ValueError('A command is required')
    check_admission(96*1024**2)
    name='eh158-job-'+secrets.token_hex(5)
    try:
        result=subprocess.run(scope_command(name,cmd),timeout=300)
    except subprocess.TimeoutExpired:
        subprocess.run(['systemctl','--user','stop',name+'.scope'],capture_output=True,timeout=12)
        target=pathlib.Path(__file__).resolve().parents[1]/'evidence'/(name+'-timeout.json')
        target.write_text(json.dumps({'status':'FAIL','reason':'controlled_job_timeout','scope':name,
            'owned_scope_stopped':True,'automatic_retry':False},indent=2)+'\n')
        raise
    sys.exit(result.returncode)


if __name__=='__main__':main()

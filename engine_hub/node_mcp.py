"""Read-only stdio MCP installed on one node; no arbitrary path or draft read tool."""
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

HOME=pathlib.Path(os.environ['HERMES_HOME'])
CONFIG=json.loads((HOME/'companion-config.json').read_text())
NODE=CONFIG['node']


def evidence(args):
    if set(args)-{'context_id'} or not re.fullmatch(r'[a-f0-9]{32}',args.get('context_id','')):
        raise ValueError('Explicit approved context required; arbitrary paths unavailable')
    url=NODE['state_url']+'/v1/contexts/'+args['context_id']+'/consume'
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+NODE['consume_key']})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req,timeout=20) as resp:
        assets=json.loads(resp.read(1000000))
    adoption=json.loads((HOME/'adoption.json').read_text())
    result={'marker':'REAL_NODE_IDENTITY','node':NODE['id'],'engine':NODE['engine'],
        'memory_marker':(HOME/'memories/MEMORY.md').read_text(),
        'workspace_marker':pathlib.Path('/workspace/node-evidence.txt').read_text(),
        'other_node_paths_denied':not any(pathlib.Path(p).exists() for p in adoption['other_host_paths']),
        'fixture':'DETERMINISTIC_MODEL_REAL_HERMES_MCP_WEKNORA_SYNTHETIC_CONTENT',**assets}
    with pathlib.Path('/workspace/mcp-evidence.jsonl').open('a') as f:
        f.write(json.dumps(result)+'\n')
    return json.dumps(result)


for line in sys.stdin:
    d=json.loads(line)
    if 'id' not in d:
        continue
    if d['method']=='initialize':
        result={'protocolVersion':d.get('params',{}).get('protocolVersion','2025-03-26'),
            'capabilities':{'tools':{}},'serverInfo':{'name':'engine-hub-readonly','version':'1'}}
    elif d['method']=='tools/list':
        result={'tools':[{'name':'ops_evidence','description':'Consume approved pinned remote knowledge and Skill method/script/reference; return actual node identity.',
            'inputSchema':{'type':'object','properties':{'context_id':{'type':'string'}},'required':['context_id'],'additionalProperties':False}}]}
    elif d['method']=='tools/call':
        try:
            if d['params']['name']!='ops_evidence':
                raise ValueError('Unknown tool')
            result={'content':[{'type':'text','text':evidence(d['params'].get('arguments',{}))}],'isError':False}
        except Exception as e:
            result={'content':[{'type':'text','text':'Approved asset access refused: '+type(e).__name__}],'isError':True}
    else:
        result={}
    print(json.dumps({'jsonrpc':'2.0','id':d['id'],'result':result}),flush=True)

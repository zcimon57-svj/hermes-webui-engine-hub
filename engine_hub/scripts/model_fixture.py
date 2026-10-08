#!/usr/bin/env python3
"""Deterministic model protocol fixture; calls real MCP, no diagnostic claim."""
import json,time,threading,hashlib,re,pathlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=pathlib.Path(__file__).resolve().parents[1]
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,obj):
  b=json.dumps(obj).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):self.send({'object':'list','data':[{'id':'webui-node-fixture','object':'model','owned_by':'local-fixture'}]})
 def do_POST(self):
  d=json.loads(self.rfile.read(int(self.headers['Content-Length'])));msgs=d.get('messages',[]);useridx=max((i for i,m in enumerate(msgs) if m.get('role')=='user'),default=-1);recent=msgs[useridx+1:];called=[t['function']['name'] for m in recent for t in m.get('tool_calls',[])];names=[t['function']['name'] for t in d.get('tools',[])];tools=[m for m in recent if m.get('role')=='tool'];identity=next((m for m in reversed(tools) if 'REAL_NODE_IDENTITY' in str(m.get('content',''))),None);call=None
  match=re.search(r'HUB_CONTEXT=([a-f0-9]{32})',str(msgs[useridx].get('content',''))) if useridx>=0 else None
  arguments={'context_id':match.group(1)} if match else {}
  if identity is None:
   if 'skill_view' in names and 'skill_view' not in called:call=('skill_view',{'name':'engine-ops'})
   else:
    ops=next((n for n in names if 'ops_evidence' in n),None)
    if ops:
     match=re.search(r'HUB_CONTEXT=([a-f0-9]{32})',str(msgs[useridx].get('content',''))) if useridx>=0 else None
     call=(ops,{'context_id':match.group(1)} if match else {})
    elif 'tool_describe' in names and 'tool_describe' not in called:call=('tool_describe',{'names':['mcp__ops__ops_evidence']})
    elif 'tool_call' in names:call=('tool_call',{'calls':[{'name':'mcp__ops__ops_evidence','arguments':arguments}]})
  text=str(msgs[useridx].get('content','')) if useridx>=0 else '';delay=re.search(r'FIXTURE_DELAY=(\d+)',text)
  if delay and not tools:time.sleep(min(int(delay.group(1)),8))
  if call:msg={'role':'assistant','content':None,'tool_calls':[{'id':'call_'+str(time.time_ns()),'type':'function','function':{'name':call[0],'arguments':json.dumps(call[1])}}]};finish='tool_calls'
  else:msg={'role':'assistant','content':'SYNTHETIC_PROTOCOL_REPORT\n'+str(identity.get('content','') if identity else tools[-1].get('content','') if tools else 'NO_MCP_EVIDENCE')};finish='stop'
  response={'id':'fixture-'+str(time.time_ns()),'object':'chat.completion','created':int(time.time()),'model':'webui-node-fixture','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':25,'completion_tokens':35,'total_tokens':60}}
  # Save only protocol metadata, no request or token values.
  with (ROOT/'.local/model-calls.jsonl').open('a') as f:f.write(json.dumps({'at':time.time(),'tool_call':call[0] if call else None,'has_identity':identity is not None,'model':d.get('model')})+'\n')
  if d.get('stream'):
   self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers();delta=msg.copy()
   for i,t in enumerate(delta.get('tool_calls',[])):t['index']=i
   for dd,ff in [(delta,None),({},finish)]:self.wfile.write(('data: '+json.dumps({**response,'object':'chat.completion.chunk','choices':[{'index':0,'delta':dd,'finish_reason':ff}]})+'\n\n').encode());self.wfile.flush()
   self.wfile.write(b'data: [DONE]\n\n')
  else:self.send(response)
if __name__=='__main__':
 from engine_hub.resources import require_containment
 from engine_hub.common import BoundedServer
 require_containment()
 BoundedServer(('127.0.0.1',15803),H,None,max_connections=8).serve_forever()

from http.server import BaseHTTPRequestHandler,HTTPServer
import json,hashlib
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  d=json.loads(self.rfile.read(int(self.headers['Content-Length'])));inputs=d.get('input',[]);inputs=inputs if isinstance(inputs,list) else [inputs]
  result={'object':'list','data':[{'object':'embedding','index':i,'embedding':[int(x)/255 for x in hashlib.sha256(str(v).encode()).digest()]*12} for i,v in enumerate(inputs)],'model':'goal6n-embedding-fixture','usage':{'prompt_tokens':1,'total_tokens':1}}
  b=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
HTTPServer(('0.0.0.0',8080),Handler).serve_forever()

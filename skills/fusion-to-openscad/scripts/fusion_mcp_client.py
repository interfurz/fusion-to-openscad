"""Fusion MCP transport/extraction helper, not a CAD converter."""
import argparse
import json
import pathlib
import urllib.request

class Client:
    def __init__(self, endpoint, timeout=180):
        self.endpoint=endpoint; self.timeout=timeout; self.sequence=0
        self.headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
    def request(self, method, params=None, notification=False):
        payload={'jsonrpc':'2.0','method':method}
        if params is not None: payload['params']=params
        if not notification:
            self.sequence+=1; payload['id']=self.sequence
        req=urllib.request.Request(self.endpoint,data=json.dumps(payload).encode(),headers=self.headers)
        with urllib.request.urlopen(req,timeout=self.timeout) as response:
            session=response.headers.get('Mcp-Session-Id')
            if session: self.headers['Mcp-Session-Id']=session
            raw=response.read().decode('utf-8')
        if notification: return None
        try: result=json.loads(raw)
        except json.JSONDecodeError:
            candidates=[json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith('data:')]
            matches=[o for o in candidates if o.get('id')==self.sequence]
            if not matches: raise RuntimeError('No matching JSON-RPC response: '+raw[:1000])
            result=matches[-1]
        if 'error' in result: raise RuntimeError(json.dumps(result['error']))
        return result
    def initialize(self):
        result=self.request('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'fusion-to-openscad-skill','version':'0.5.1'}})
        self.request('notifications/initialized',notification=True)
        return result

def checked_content(response):
    result=response['result']
    if result.get('isError'): raise RuntimeError(json.dumps(result))
    outputs=[]
    for item in result.get('content',[]):
        if item.get('type')!='text': continue
        text=item.get('text','')
        try: value=json.loads(text)
        except json.JSONDecodeError: value=text
        if isinstance(value,dict) and value.get('success') is False: raise RuntimeError(json.dumps(value))
        if isinstance(value,dict) and isinstance(value.get('message'),str):
            try: value['parsed_message']=json.loads(value['message'])
            except json.JSONDecodeError: pass
        outputs.append(value)
    return outputs

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--endpoint',required=True)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--read',help='JSON arguments for the discovered read tool')
    mode.add_argument('--script',type=pathlib.Path,help='Python API request executed inside Fusion')
    mode.add_argument('--list-tools',action='store_true')
    p.add_argument('--allow-design-changes',action='store_true',help='ONLY for an identified disposable copy')
    p.add_argument('--export-dir',type=pathlib.Path)
    p.add_argument('--source-label',default='')
    p.add_argument('--output',type=pathlib.Path,required=True)
    a=p.parse_args()
    client=Client(a.endpoint); client.initialize()
    tools=client.request('tools/list',{})
    schemas={t['name']:t for t in tools['result']['tools']}
    if a.list_tools: result=tools
    else:
        if a.read:
            name='fusion_mcp_read';arguments=json.loads(a.read)
        else:
            name='fusion_mcp_execute';script=a.script.read_text(encoding='utf-8')
            if a.export_dir:
                a.export_dir.mkdir(parents=True,exist_ok=True)
                script='HERMES_FUSION_OUTPUT_DIR='+repr(str(a.export_dir.resolve()))+'\nHERMES_FUSION_SOURCE_LABEL='+repr(a.source_label)+'\n'+script
            arguments={'featureType':'script','object':{'script':script,'readOnly':not a.allow_design_changes}}
        if name not in schemas: raise RuntimeError('Expected tool not exposed; inspect actual schemas: '+name)
        result=client.request('tools/call',{'name':name,'arguments':arguments})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    outputs=checked_content(result) if not a.list_tools else tools['result']
    print(json.dumps(outputs,indent=2,ensure_ascii=False))

if __name__=='__main__': main()

"""Offline regression tests for transport; optional mesh tests."""
import json,pathlib,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import fusion_mcp_client as transport

class Response:
    def __init__(self,data,session=None):
        self.data=data.encode();self.headers={'Mcp-Session-Id':session} if session else {}
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self): return self.data

class TransportTests(unittest.TestCase):
    def test_initialize_notification_and_session(self):
        seen=[]
        def send(req,timeout):
            payload=json.loads(req.data);seen.append((payload,dict(req.header_items())))
            if payload['method']=='initialize': return Response(json.dumps({'jsonrpc':'2.0','id':1,'result':{}}),'session-test')
            return Response('')
        with patch('urllib.request.urlopen',side_effect=send):transport.Client('http://localhost/mcp').initialize()
        self.assertEqual(seen[1][0]['method'],'notifications/initialized')
        self.assertNotIn('id',seen[1][0])
        self.assertEqual(next(v for k,v in seen[1][1].items() if k.lower()=='mcp-session-id'),'session-test')
    def test_sse_reply(self):
        raw='event: message\ndata: '+json.dumps({'jsonrpc':'2.0','id':1,'result':{'ok':True}})+'\n\n'
        with patch('urllib.request.urlopen',return_value=Response(raw)):
            self.assertTrue(transport.Client('http://localhost/mcp').request('tools/list')['result']['ok'])
    def test_rpc_error(self):
        raw=json.dumps({'jsonrpc':'2.0','id':1,'error':{'code':-32600,'message':'failed'}})
        with patch('urllib.request.urlopen',return_value=Response(raw)):
            with self.assertRaises(RuntimeError):transport.Client('http://localhost/mcp').request('tools/list')
    def test_nested_error(self):
        raw={'result':{'content':[{'type':'text','text':json.dumps({'success':False,'error':'runtime failure'})}]}}
        with self.assertRaises(RuntimeError):transport.checked_content(raw)
    def test_nested_printed_json(self):
        raw={'result':{'content':[{'type':'text','text':json.dumps({'success':True,'message':json.dumps({'bodies':2})})}]}}
        self.assertEqual(transport.checked_content(raw)[0]['parsed_message']['bodies'],2)

class ParameterClassificationTests(unittest.TestCase):
    def setUp(self):
        import ast,types
        source=(pathlib.Path(__file__).parent/'fusion_extract.py').read_text(encoding='utf-8')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='parameter_record')
        self.User=type('UserParameter',(),{})
        self.Model=type('ModelParameter',(),{})
        scope={'adsk':types.SimpleNamespace(fusion=types.SimpleNamespace(UserParameter=self.User))}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<parameter_record>','exec'),scope)
        self.record=scope['parameter_record']
    def make(self,cls,name):
        p=cls();p.name=name;p.expression='-5 mm';p.value=-0.5;p.unit='mm';p.comment='Signed extrusion'
        return p
    def test_real_user_parameter_preserves_source_metadata(self):
        r=self.record(self.make(self.User,'Thickness'))
        self.assertEqual(r['kind'],'user')
        self.assertEqual(r['expression'],'-5 mm')
        self.assertEqual(r['value'],-0.5)
    def test_model_parameter_is_not_user_based_on_its_name(self):
        self.assertEqual(self.record(self.make(self.Model,'Width'))['kind'],'model')

class MeshTests(unittest.TestCase):
    def setUp(self):
        try:
            import verify_mesh,trimesh
            self.v=verify_mesh;self.t=trimesh
        except ImportError:self.skipTest('Mesh validation dependencies not installed')
    def test_equal_boxes(self):
        a=self.t.creation.box(extents=[10,20,30]);r=self.v.compare(a,a.copy(),True)
        self.assertEqual(r['generated_components'],1)
        self.assertAlmostEqual(r['extra_volume_mm3'],0,places=6)
        self.assertAlmostEqual(r['generated_to_reference']['maximum_observed_mm'],0,places=6)
    def test_shift_is_detected_despite_equal_volume(self):
        a=self.t.creation.box(extents=[10,20,30]);b=a.copy();b.apply_translation([1,0,0]);r=self.v.compare(a,b,True)
        self.assertAlmostEqual(r['volume_difference_mm3'],0)
        self.assertGreater(r['extra_volume_mm3'],0)
        self.assertAlmostEqual(r['bounds_max_difference_mm'],1)

if __name__=='__main__':unittest.main(verbosity=2)

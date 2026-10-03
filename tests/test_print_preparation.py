"""Generic preparation tests; all geometry is generated in temporary fixtures."""
import importlib.util,json,os,pathlib,subprocess,sys,tempfile,unittest,xml.etree.ElementTree as ET,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_print',ROOT/'scripts/prepare_print.py')
prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)

class PreparationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder=pathlib.Path(temporary.name)
        self.template=self.folder/'fixture.scad'
        self.template.write_text('''// ROOT_FREE_TEMPLATE
/* [Fusion User Parameters] */
// Width of the first test solid (mm).
Width = 20; // [10:1:30]
// Height of the first test solid (mm).
Height = 10; // [5:1:20]
/* [Hidden] */
assert(Width>=10 && Width<=30, "Width must be between 10 and 30 mm.");
assert(Height>=5 && Height<=20, "Height must be between 5 and 20 mm.");
module mw_plate_1() { translate([5,5,0]) cube([Width,Height,2]); }
module mw_plate_2() { translate([5,5,0]) cube([5,5,3]); }
module mw_assembly_view() { mw_plate_1(); translate([40,0,0]) mw_plate_2(); }
''',encoding='utf-8')
        self.config=self.folder/'fixture.json'
        config={'schema_version':1,'source':'fixture.scad','defaults':{'Width':20,'Height':10},'ranges':{'Width':{'min':10,'max':30},'Height':{'min':5,'max':20}},'gap_mm':8,'margin_mm':5,'bed_mm':64,'parts':[{'name':'Part_A','module':'mw_plate_1','width_expression':'Width','height_expression':'Height'},{'name':'Part_B','module':'mw_plate_2','width_expression':'5','height_expression':'5'}]}
        self.config.write_text(json.dumps(config),encoding='utf-8')
        self.output=self.folder/'output'

    def test_generation_separates_print_and_assembly(self):
        _,_,mw,printing,parts=prep.prepare(self.config,self.output)
        text=printing.read_text();self.assertTrue(text.endswith('print_layout();\n'))
        self.assertNotIn('mw_plate_',text)
        self.assertNotIn('mw_assembly_view',text)
        self.assertEqual(len(parts),2)
        self.assertIn('if ($preview) print_layout(false);',mw.read_text())
        self.assertIn('print_gap = 8;',text)

    def test_defaults_and_parameter_override(self):
        _,values,mw,_,_=prep.prepare(self.config,self.output,{'Width':25})
        self.assertEqual(values['Width'],25);self.assertIn('Width = 25;',mw.read_text())

    def test_outside_range_rejected(self):
        with self.assertRaisesRegex(ValueError,'Width'):
            prep.prepare(self.config,self.output,{'Width':300})

    def test_unknown_parameter_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unknown'):
            prep.prepare(self.config,self.output,{'unknown':1})

    def test_non_finite_rejected(self):
        for value in [float('nan'),float('inf'),True,'20']:
            with self.subTest(value=value),self.assertRaises(ValueError):prep.number(value)

    def test_no_root_free_marker_is_rejected(self):
        self.template.write_text('cube(10);',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'ROOT_FREE'):
            prep.prepare(self.config,self.output)

    def test_duplicate_names_rejected(self):
        config=json.loads(self.config.read_text())
        config['parts'][1]['name']=config['parts'][0]['name']
        self.config.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError,'Duplicate'):prep.load_config(self.config)

    def test_named_3mf_objects_are_independent_build_items(self):
        try:import trimesh
        except ImportError:self.skipTest('optional trimesh not installed')
        a=trimesh.creation.box(extents=[10,10,2])
        b=trimesh.creation.box(extents=[3,3,3]);b.apply_translation([20,0,0])
        path=self.folder/'parts.3mf';prep.export_3mf(path,[('Part_A',a),('Part_B',b)])
        with zipfile.ZipFile(path) as z:root=ET.fromstring(z.read('3D/3dmodel.model'))
        objects=root.findall('{'+prep.CORE+'}resources/{'+prep.CORE+'}object')
        items=root.findall('{'+prep.CORE+'}build/{'+prep.CORE+'}item')
        self.assertEqual([o.attrib['name'] for o in objects],['Part_A','Part_B'])
        self.assertEqual([i.attrib['objectid'] for i in items],['1','2'])
        scene=trimesh.load(path,force='scene');self.assertEqual(len(scene.geometry),2)

    def test_empty_3mf_rejected(self):
        with self.assertRaises(ValueError):prep.export_3mf(self.folder/'empty.3mf',[])

    def test_generated_user_interface_is_english(self):
        _,_,mw,printing,_=prep.prepare(self.config,self.output)
        for path in [mw,printing]:
            text=path.read_text()
            self.assertIn('/* [Fusion User Parameters] */',text)
            self.assertIn('Parts do not fit together on this bed.',text)
            self.assertEqual(text.count('/* [Fusion User Parameters] */'),1)

    @unittest.skipUnless(os.environ.get('OPENSCAD_EXE'),'set OPENSCAD_EXE to enable real rendering')
    def test_cli_real_render_produces_two_named_objects(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/prepare_print.py'),'--config',str(self.config),'--output',str(self.output),'--render','--openscad',os.environ['OPENSCAD_EXE']],capture_output=True,text=True,timeout=180)
        self.assertEqual(result.returncode,0,result.stderr)
        summary=json.loads(result.stdout)['verification']
        self.assertEqual(summary['combined_connected_solids'],2)
        self.assertEqual(summary['combined_3mf_named_objects'],['Part_A','Part_B'])
        self.assertTrue(summary['passed'])
        self.assertEqual(len(summary['objects']),2)
        self.assertTrue(all(obj['watertight'] for obj in summary['objects']))

if __name__=='__main__':unittest.main()

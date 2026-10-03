#!/usr/bin/env python
"""Prepare already-reconstructed parametric SCAD as separate printable objects.

This is not an arbitrary Fusion/F3D geometry converter. Model-specific geometry
must be supplied in a root-free SCAD template; the Fusion skill handles reconstruction.
Generation uses Python's standard library. --render additionally needs numpy/trimesh.
"""
import argparse,hashlib,json,math,pathlib,re,shutil,subprocess,sys,xml.etree.ElementTree as ET,zipfile
CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CTYPE='http://schemas.openxmlformats.org/package/2006/content-types'
IDENT=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

def number(value):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):
        raise ValueError('Expected a finite number, got '+repr(value))
    return format(value,'.12g')

def load_config(path):
    config=json.loads(path.read_text(encoding='utf-8'))
    if config.get('schema_version')!=1:raise ValueError('Unsupported configuration schema')
    source=(path.parent/config['source']).resolve()
    if not source.is_file():raise ValueError('SCAD template missing: '+str(source))
    seen=set()
    for part in config['parts']:
        if not IDENT.fullmatch(part['name']) or not IDENT.fullmatch(part['module']):raise ValueError('Invalid object/module identifier')
        if part['name'] in seen:raise ValueError('Duplicate object name')
        seen.add(part['name'])
    if len(config['parts'])<2:raise ValueError('Use at least two distinct part modules')
    return config,source

def prepare(config_path,output,overrides=None):
    config,source=load_config(config_path)
    text=source.read_text(encoding='utf-8')
    if '// ROOT_FREE_TEMPLATE' not in text:raise ValueError('Template must explicitly declare // ROOT_FREE_TEMPLATE and contain no root geometry calls')
    values=dict(config['defaults']);values.update(overrides or {})
    if set(values)!=set(config['defaults']):raise ValueError('Unknown parameter override')
    for key,value in values.items():
        if not IDENT.fullmatch(key):raise ValueError('Invalid parameter name')
        number(value)
        bounds=config['ranges'][key]
        if value<bounds['min'] or value>bounds['max']:raise ValueError(f'{key}: allowed range {bounds["min"]} .. {bounds["max"]}')
        pattern=r'^(\s*'+re.escape(key)+r'\s*=\s*)[^;]+;'
        text,count=re.subn(pattern,lambda m:m[1]+number(value)+';',text,flags=re.M)
        if count!=1:raise ValueError(f'{key}: expected exactly one top-level assignment')
    for part in config['parts']:
        if not re.search(r'\bmodule\s+'+re.escape(part['module'])+r'\s*\(',text):raise ValueError('Module missing: '+part['module'])
    output.mkdir(parents=True,exist_ok=True)
    gap=config.get('gap_mm',8);margin=config.get('margin_mm',5);bed=config.get('bed_mm',256)
    for value in [gap,margin,bed]:number(value)
    if gap<=0 or margin<0 or bed<=0:raise ValueError('Invalid gap/margin/bed')
    widths=[p['width_expression'] for p in config['parts']]
    heights=[p['height_expression'] for p in config['parts']]
    # Expressions come from the trusted local model configuration, not user input.
    layout='\n// Automatically prepared PRINT layout: distinct parts with a real gap.\n'
    layout+='print_gap = '+number(gap)+';\n'
    layout+='print_bed = '+number(bed)+';\n'
    layout+='print_margin = '+number(margin)+';\n'
    layout+='print_total_width = '+'+'.join('('+w+')' for w in widths)+f'+{len(widths)-1}*print_gap+2*print_margin;\n'
    layout+='print_total_height = max(['+','.join(heights)+'])+2*print_margin;\n'
    layout+='module print_layout(check_bed=true) {\n'
    layout+='    assert(!check_bed || (print_total_width<=print_bed && print_total_height<=print_bed), "Parts do not fit together on this bed. Use the separate-plate MakerWorld file or smaller dimensions.");\n'
    for i,part in enumerate(config['parts']):
        dx='0' if i==0 else '+'.join('('+w+')' for w in widths[:i])+f'+{i}*print_gap'
        layout+='    translate(['+dx+',0,0]) '+part['module']+'();\n'
    layout+='}\n'
    # MakerWorld calls plate modules for manufacture. Its assembly view is still
    # retained separately; desktop F5 now shows separated parts, not an assembly.
    makerworld=output/'Model-MakerWorld.scad'
    makerworld.write_text(text+layout+'\nif ($preview) print_layout(false);\n',encoding='utf-8')
    # Ordinary OpenSCAD file is NOT a PMM multi-plate source: remove reserved
    # output module names so MakerWorld cannot accidentally add other plates.
    ordinary=text+layout
    rename={p['module']:'print_part_'+str(i+1) for i,p in enumerate(config['parts'])}
    rename['mw_assembly_view']='assembly_view'
    for old,new in rename.items():ordinary=re.sub(r'\b'+re.escape(old)+r'\b',new,ordinary)
    print_source=output/'Model-Print.scad'
    print_source.write_text(ordinary+'\nprint_layout();\n',encoding='utf-8')
    separate=[]
    for i,part in enumerate(config['parts']):
        path=output/(part['name']+'.scad')
        path.write_text(text+'\n'+part['module']+'();\n',encoding='utf-8')
        separate.append(path)
    return config,values,makerworld,print_source,separate

def export_3mf(path,named_meshes):
    """Write a Core 3MF with one named resource AND one build item per part."""
    if not named_meshes:raise ValueError('No 3MF objects')
    ET.register_namespace('',CORE)
    root=ET.Element('{'+CORE+'}model',{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
    resources=ET.SubElement(root,'{'+CORE+'}resources');build=ET.SubElement(root,'{'+CORE+'}build')
    for index,(name,mesh) in enumerate(named_meshes,1):
        obj=ET.SubElement(resources,'{'+CORE+'}object',{'id':str(index),'name':name,'type':'model'})
        m=ET.SubElement(obj,'{'+CORE+'}mesh');vertices=ET.SubElement(m,'{'+CORE+'}vertices');triangles=ET.SubElement(m,'{'+CORE+'}triangles')
        for v in mesh.vertices:ET.SubElement(vertices,'{'+CORE+'}vertex',dict(zip(['x','y','z'],[number(float(x)) for x in v])))
        for face in mesh.faces:ET.SubElement(triangles,'{'+CORE+'}triangle',dict(zip(['v1','v2','v3'],map(lambda x:str(int(x)),face))))
        ET.SubElement(build,'{'+CORE+'}item',{'objectid':str(index)})
    content=ET.Element('Types',{'xmlns':CTYPE})
    ET.SubElement(content,'Default',{'Extension':'rels','ContentType':'application/vnd.openxmlformats-package.relationships+xml'})
    ET.SubElement(content,'Override',{'PartName':'/3D/3dmodel.model','ContentType':'application/vnd.ms-package.3dmanufacturing-3dmodel+xml'})
    relationships=ET.Element('Relationships',{'xmlns':REL})
    ET.SubElement(relationships,'Relationship',{'Target':'/3D/3dmodel.model','Id':'rel0','Type':'http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel'})
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,element in [('[Content_Types].xml',content),('_rels/.rels',relationships),('3D/3dmodel.model',root)]:z.writestr(name,ET.tostring(element,encoding='utf-8',xml_declaration=True))
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('Invalid 3MF package')
        xml=ET.fromstring(z.read('3D/3dmodel.model'))
        objects=xml.findall('{'+CORE+'}resources/{'+CORE+'}object');items=xml.findall('{'+CORE+'}build/{'+CORE+'}item')
        if len(objects)!=len(named_meshes) or len(items)!=len(named_meshes):raise ValueError('3MF object count failed')
        if [o.attrib['name'] for o in objects]!=[name for name,_ in named_meshes]:raise ValueError('3MF names failed')

def execute_render(exe,source,output,extra=()):
    r=subprocess.run([str(exe),'--hardwarnings','-D','$preview=false','-o',str(output),*extra,str(source)],capture_output=True,text=True,timeout=180)
    (output.parent/(output.name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode or 'ERROR:' in r.stderr or 'WARNING:' in r.stderr or not output.is_file() or output.stat().st_size==0:raise RuntimeError('OpenSCAD failed: '+r.stderr)

def render(config,values,output,separate,print_source,exe,separate_plates=False):
    try:import numpy as np;import trimesh
    except ImportError as e:raise RuntimeError('--render requires numpy and trimesh; install requirements.txt') from e
    meshes=[];report={'parameters':values,'objects':[],'separate_plates':separate_plates,'makerworld_backend_tested':False}
    # Never leave a previous combined export looking like the result of a new
    # separate-plate run or a rejected one-bed layout.
    for suffix in ['.stl','.3mf']:
        (output/('Model-Print'+suffix)).unlink(missing_ok=True)
    for part,source in zip(config['parts'],separate):
        target=output/(part['name']+'.stl');execute_render(exe,source,target)
        mesh=trimesh.load_mesh(target,process=True)
        if not isinstance(mesh,trimesh.Trimesh) or not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split(only_watertight=False))!=1 or mesh.volume<=0:raise ValueError(part['name']+': expected one valid solid')
        if abs(mesh.bounds[0,2])>0.002:raise ValueError(part['name']+': not on Z=0')
        margin=config.get('margin_mm',5);bed=config.get('bed_mm',256)
        if np.any(mesh.bounds[0,:2]<margin-0.002) or np.any(mesh.bounds[1,:2]>bed-margin+0.002):raise ValueError(part['name']+': part exceeds bed/margin')
        meshes.append((part['name'],mesh));report['objects'].append({'name':part['name'],'watertight':True,'connected_solids':1,'bounds_mm':mesh.bounds.tolist(),'volume_mm3':float(mesh.volume)})
        export_3mf(output/(part['name']+'.3mf'),[(part['name'],mesh)])
    if not separate_plates:
        arranged=[];dx=0;gap=config.get('gap_mm',8)
        for name,mesh in meshes:
            copy=mesh.copy();copy.apply_translation([dx,0,0]);arranged.append((name,copy));dx+=mesh.extents[0]+gap
        bounds=np.vstack([m.bounds for _,m in arranged])
        bed=config.get('bed_mm',256);margin=config.get('margin_mm',5)
        if np.any(bounds[:,:2]>bed-margin+0.002):raise ValueError('Combined layout does not fit. Use --separate-plates or smaller parameters. Individual files were generated.')
        execute_render(exe,print_source,output/'Model-Print.stl')
        together=trimesh.load_mesh(output/'Model-Print.stl',process=True)
        if len(together.split(only_watertight=False))!=len(meshes):raise ValueError('Combined SCAD did not produce distinct disconnected solids')
        export_3mf(output/'Model-Print.3mf',arranged)
        # Parse the complete 3MF through an independent library and count solids.
        scene=trimesh.load(output/'Model-Print.3mf',force='scene')
        if len(scene.geometry)!=len(meshes):raise ValueError('Independent 3MF read-back object count failed')
        report['combined_3mf_named_objects']=[name for name,_ in arranged]
        report['combined_connected_solids']=len(together.split(only_watertight=False))
        report['gap_mm']=gap
    report['passed']=True
    (output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=pathlib.Path,required=True)
    parser.add_argument('--output',type=pathlib.Path,required=True)
    parser.add_argument('--set',action='append',default=[],metavar='NAME=NUMBER')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--openscad',type=pathlib.Path)
    parser.add_argument('--separate-plates',action='store_true',help='Skip combined bed export; output one 3MF per part')
    args=parser.parse_args();overrides={}
    try:
        for setting in args.set:
            name,value=setting.split('=',1)
            if name in overrides:raise ValueError('Duplicate override: '+name)
            overrides[name]=float(value)
        config,values,mw,printing,separate=prepare(args.config.resolve(),args.output.resolve(),overrides)
        summary={'generated_scad':[str(mw),str(printing),*[str(p) for p in separate]],'parameters':values,'scope':'Printing preparation for a supplied parametric SCAD reconstruction; NOT an arbitrary F3D converter.'}
        if args.render:
            exe=args.openscad or shutil.which('openscad')
            if not exe:raise ValueError('OpenSCAD not found: pass --openscad PATH')
            summary['verification']=render(config,values,args.output.resolve(),separate,printing,exe,args.separate_plates)
        print(json.dumps(summary,indent=2));return 0
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as e:
        print('ERROR: '+str(e),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())

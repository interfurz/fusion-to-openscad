"""Execute INSIDE Fusion through the MCP client, not local Python.
Set HERMES_FUSION_OUTPUT_DIR and optionally HERMES_FUSION_SOURCE_LABEL
by using the client's --export-dir and --source-label arguments.
This is an extensible common-feature extractor, NOT a CAD converter.
Timeline changes require an explicitly identified disposable copy.
"""
import adsk.core, adsk.fusion, json, pathlib
OUT=pathlib.Path(globals()['HERMES_FUSION_OUTPUT_DIR'])
SOURCE_LABEL=globals().get('HERMES_FUSION_SOURCE_LABEL','')
ERRORS=[]
def ref(o):
    if o is None:return None
    d={'type':o.objectType}
    for n in ('name','entityToken','tempId'):
        try:d[n]=getattr(o,n)
        except AttributeError:continue
        except RuntimeError as exc:ERRORS.append({'type':o.objectType,'property':n,'error':str(exc)})
    return d

def val(o,depth=0):
    if o is None or isinstance(o,(str,int,float,bool)):return o
    if isinstance(o,(tuple,list)):return [val(x,depth+1) for x in o]
    if hasattr(o,'asArray'):return [val(x,depth+1) for x in o.asArray()]
    if hasattr(o,'count') and hasattr(o,'item'):return [val(o.item(i),depth+1) for i in range(o.count)]
    return ref(o)

def props(o,names):
    r={}
    for n in names:
        try:r[n]=val(getattr(o,n))
        except AttributeError:continue
        except RuntimeError as exc:ERRORS.append({'type':o.objectType,'property':n,'error':str(exc)})
    return r

def geo(o):
    if o.objectType not in {'adsk::core::Line3D','adsk::core::Arc3D','adsk::core::Circle3D','adsk::core::Plane','adsk::core::Cylinder','adsk::core::Cone','adsk::core::Sphere','adsk::core::Torus'}:
        ERRORS.append({'type':o.objectType,'property':'geometry','error':'Needs case-specific geometry extraction'})
    return {'type':o.objectType,**props(o,['startPoint','endPoint','center','radius','normal','origin','axis','majorRadius','minorRadius','startAngle','endAngle','referenceVector','direction','uDirection','vDirection','halfAngle'])}

def edge(e):
    return {'ref':ref(e),'geometry':geo(e.geometry),'start':val(e.startVertex.geometry) if e.startVertex else None,'end':val(e.endVertex.geometry) if e.endVertex else None,'length_cm':e.length,'faces':[ref(f) for f in e.faces]}

def curve(c):
    return {'ref':ref(c),'geometry':geo(c.geometry),**props(c,['isConstruction','isReference','startSketchPoint','endSketchPoint','centerSketchPoint'])}

def profile(p):
    return {'ref':ref(p),'sketch':ref(p.parentSketch),'loops':[{'outer':loop.isOuter,'curves':[{'geometry':geo(pc.geometry),'sketch_curve':ref(pc.sketchEntity)} for pc in loop.profileCurves]} for loop in p.profileLoops]}

def extent(e):
    if e is None:return None
    r={'type':e.objectType,**props(e,['distance','offset','entity','isChained','isMinimumSolution','direction','isPositiveDirection'])}
    for n in ('distance','offset'):
        if hasattr(e,n):
            p=getattr(e,n)
            if p is not None and hasattr(p,'expression'):r[n]={'name':p.name,'expression':p.expression,'value':p.value,'unit':p.unit}
    return r

def parameter_record(p):
    return {'name':p.name,'expression':p.expression,'value':p.value,'unit':p.unit,'comment':p.comment,'kind':'user' if isinstance(p,adsk.fusion.UserParameter) else 'model'}

def run_inner(_context: str):
    app=adsk.core.Application.get();d=adsk.fusion.Design.cast(app.activeProduct)
    r={'schema_version':'0.1','units':{'length':'cm','angle':'rad','volume':'cm3'},'source':SOURCE_LABEL,'document':app.activeDocument.name,'parameters':[],'occurrences':[],'sketches':[],'features':[],'bodies':[]}
    assert d is not None, 'An active Fusion design is required'
    assert d.timeline.markerPosition==d.timeline.count, 'Start at the final timeline state in a disposable copy'
    OUT.mkdir(parents=True,exist_ok=True)
    r['application_version']=app.version
    r['design_type']=d.designType
    r['marker_position']=d.timeline.markerPosition
    r['needs_case_specific_export']=[]
    r['user_parameters']=[parameter_record(p) for p in d.userParameters]
    for p in d.allParameters:r['parameters'].append(parameter_record(p))
    for o in d.rootComponent.allOccurrences:r['occurrences'].append({'name':o.name,'component':o.component.name,'transform':val(o.transform2)})
    for c in d.allComponents:
        for s in c.sketches:
            sr={'ref':ref(s),'index':s.timelineObject.index,'origin':val(s.origin),'x':val(s.xDirection),'y':val(s.yDirection),'transform':val(s.transform),'curves':[curve(x) for x in s.sketchCurves],'profiles':[profile(p) for p in s.profiles],'dimensions':[],'constraints':[]}
            for dim in s.sketchDimensions:
                p=dim.parameter
                sr['dimensions'].append({'ref':ref(dim),'parameter':{'name':p.name,'expression':p.expression,'value':p.value,'unit':p.unit},**props(dim,['entityOne','entityTwo','line','entity','orientation','isDriving','textPosition'])})
            for co in s.geometricConstraints:sr['constraints'].append({'ref':ref(co),**props(co,['entityOne','entityTwo','entityThree','entity','line','point','curve','curveOne','curveTwo','symmetryLine'])})
            r['sketches'].append(sr)
        for b in c.bRepBodies:
            bb=b.preciseBoundingBox
            br={'ref':ref(b),'component':c.name,'volume':b.volume,'area':b.area,'min':val(bb.minPoint),'max':val(bb.maxPoint),'edges':[edge(e) for e in b.edges],'faces':[]}
            for f in b.faces:br['faces'].append({'ref':ref(f),'area':f.area,'geometry':geo(f.geometry),'point':val(f.pointOnFace),'normal_reversed':f.isParamReversed,'loops':[{'outer':l.isOuter,'edges':[ref(e) for e in l.edges]} for l in f.loops]})
            temporary=adsk.fusion.TemporaryBRepManager.get().copy(b)
            assert temporary
            calc=temporary.meshManager.createMeshCalculator();calc.surfaceTolerance=0.0005
            mesh=calc.calculate();assert mesh
            import re
            stem=str(len(r['bodies'])+1).zfill(3)+'_'+re.sub(r'[^A-Za-z0-9_-]','_',c.name)+'_'+re.sub(r'[^A-Za-z0-9_-]','_',b.name)
            br['reference_mesh']=stem+'-reference-mesh.json'
            (OUT/br['reference_mesh']).write_text(json.dumps({'nodes':[val(p) for p in mesh.nodeCoordinates],'indices':list(mesh.nodeIndices),'units':'cm','tolerance_cm':0.0005}),encoding='utf-8')
            r['bodies'].append(br)
    for i in range(d.timeline.count):
        t=d.timeline.item(i);f=t.entity
        fr={'index':i,'name':t.name,'ref':ref(f),'suppressed':t.isSuppressed,'health':t.healthState,'message':t.errorOrWarningMessage}
        if f and not t.isSuppressed:
            known=(adsk.fusion.Sketch,adsk.fusion.ExtrudeFeature,adsk.fusion.FilletFeature,adsk.fusion.CombineFeature,adsk.fusion.ConstructionPlane,adsk.fusion.Occurrence)
            if not isinstance(f,known):r['needs_case_specific_export'].append({'index':i,'name':t.name,'type':f.objectType})
            if isinstance(f,(adsk.fusion.ExtrudeFeature,adsk.fusion.FilletFeature,adsk.fusion.CombineFeature)):
                assert t.rollTo(True), 'Could not roll before '+t.name
            fr.update(props(f,['operation','bodies','participantBodies','extentType','extentDirection','isSolid','isSymmetric','targetBody','toolBodies','isKeepToolBodies','isTangentChain','isRollingBallCorner']))
            if isinstance(f,adsk.fusion.ExtrudeFeature):
                p=f.profile
                ps=[p] if isinstance(p,adsk.fusion.Profile) else [p.item(j) for j in range(p.count)]
                fr['profiles']=[profile(x) for x in ps]
                fr['extent_one']=extent(f.extentOne);fr['extent_two']=extent(f.extentTwo);fr['start_extent']=extent(f.startExtent)
                fr['taper']=props(f.taperAngle,['name','expression','value','unit'])
            if isinstance(f,adsk.fusion.FilletFeature):
                fr['edge_sets']=[]
                for es in f.edgeSets:
                    er=props(es,['radius','tangencyWeight','isTangentChain','continuity'])
                    if hasattr(es,'radius'):er['radius']=props(es.radius,['name','expression','value','unit'])
                    er['edges']=[edge(e) for e in es.edges]
                    fr['edge_sets'].append(er)
        r['features'].append(fr)
    r['export_errors']=ERRORS
    (OUT/'fusion-export.json').write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'file':str(OUT/'fusion-export.json'),'bodies':len(r['bodies']),'sketches':len(r['sketches']),'features':len(r['features']),'needs_case_specific_export':r['needs_case_specific_export'],'export_errors':ERRORS},ensure_ascii=False))

def run(_context: str):
    d=adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    saved=d.timeline.markerPosition
    try:
        run_inner(_context)
    finally:
        d.timeline.markerPosition=saved

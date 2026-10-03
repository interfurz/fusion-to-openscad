"""Compare an API reference mesh with real OpenSCAD output."""
import argparse,json,pathlib
import numpy as np
import trimesh
import manifold3d

def load_reference(path):
    if path.suffix.lower()!='.json': return trimesh.load_mesh(path,process=True)
    data=json.loads(path.read_text(encoding='utf-8'))
    unit=data.get('units','cm')
    scales={'cm':10.0,'mm':1.0,'m':1000.0}
    if unit not in scales: raise ValueError('Unsupported reference unit: '+unit)
    return trimesh.Trimesh(vertices=np.asarray(data['nodes'])*scales[unit],faces=np.asarray(data['indices']).reshape(-1,3),process=True)

def as_manifold(mesh):
    result=manifold3d.Manifold(manifold3d.Mesh(vert_properties=np.asarray(mesh.vertices,dtype=np.float32),tri_verts=np.asarray(mesh.faces,dtype=np.uint32)))
    if result.status()!=manifold3d.Error.NoError: raise ValueError('Invalid manifold: '+str(result.status()))
    return result

def sampled_distances(source,target):
    points=np.vstack([source.vertices,source.triangles_center]);distances=[]
    for i in range(0,len(points),32):
        _,dist,_=trimesh.proximity.closest_point_naive(target,points[i:i+32]); distances.extend(dist)
    distances=np.asarray(distances); index=int(distances.argmax())
    return {'sample_count':len(points),'method':'all vertices and triangle centroids','maximum_observed_mm':float(distances[index]),'worst_sample_mm':points[index].tolist(),'percentiles_mm':np.percentile(distances,[50,95,99]).tolist()}

def compare(ref,gen,surface_check=False):
    if len(ref.faces)==0 or len(gen.faces)==0: raise ValueError('Empty mesh')
    if not ref.is_watertight or not gen.is_watertight: raise ValueError('Both meshes must be watertight')
    if not ref.is_winding_consistent or not gen.is_winding_consistent: raise ValueError('Inconsistent winding')
    a,b=as_manifold(ref),as_manifold(gen)
    result={'reference_bounds_mm':ref.bounds.tolist(),'generated_bounds_mm':gen.bounds.tolist(),'bounds_max_difference_mm':float(np.abs(ref.bounds-gen.bounds).max()),'reference_volume_mm3':float(ref.volume),'generated_volume_mm3':float(gen.volume),'volume_difference_mm3':float(gen.volume-ref.volume),'extra_volume_mm3':(b-a).volume(),'missing_volume_mm3':(a-b).volume(),'generated_watertight':bool(gen.is_watertight),'generated_components':len(gen.split()),'generated_faces':len(gen.faces)}
    if surface_check:
        result['generated_to_reference']=sampled_distances(gen,ref)
        result['reference_to_generated']=sampled_distances(ref,gen)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=pathlib.Path,required=True)
    p.add_argument('--generated',type=pathlib.Path,required=True)
    p.add_argument('--report',type=pathlib.Path,required=True)
    p.add_argument('--surface-check',action='store_true')
    p.add_argument('--tolerance-mm',type=float,default=0.01)
    a=p.parse_args()
    if a.tolerance_mm<=0: raise ValueError('Tolerance must be positive')
    ref=load_reference(a.reference);gen=trimesh.load_mesh(a.generated,process=True)
    result=compare(ref,gen,a.surface_check)
    result['requested_tolerance_mm']=a.tolerance_mm
    result['bounds_pass']=result['bounds_max_difference_mm']<=a.tolerance_mm
    result['body_count_pass']=result['generated_components']==1
    result['surface_samples_pass']=all(result[k]['maximum_observed_mm']<=a.tolerance_mm for k in ['generated_to_reference','reference_to_generated']) if a.surface_check else None
    result['limitations']='Sampled distances are not a proven Hausdorff bound; mesh booleans use float32. Review localized differences and source analytic metrics.'
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if not result['bounds_pass'] or not result['body_count_pass'] or result['surface_samples_pass'] is False: raise SystemExit(2)

if __name__=='__main__': main()

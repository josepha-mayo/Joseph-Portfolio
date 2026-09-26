"""Preflight tests only. No model, GPU, or fabricated inference outputs."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from PIL import Image
SCRIPT=Path(__file__).resolve().parents[1]/'gpu_acceptance.py'
spec=importlib.util.spec_from_file_location('gpu_acceptance',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
SOURCE=Path(os.environ.get('VON_ACCEPTANCE_SOURCE', str(SCRIPT.parents[1]/'exact-source')))

@pytest.fixture
def data(tmp_path):
    root=tmp_path/'data';root.mkdir();rows=[]
    for i in range(10):
        suffix,fmt=[('.png','PNG'),('.jpg','JPEG'),('.tiff','TIFF')][i%3]
        p=root/f'case_{i}{suffix}';Image.new('RGB',(32,24)).save(p,format=fmt)
        rows.append({'id':f'case_{i}','image':p.name,'sha256':m.digest(p)})
    path=root/'inputs.jsonl'
    def save():path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    save();return path,rows,save

def test_exact_source_and_three_formats(data):
    path,_,_=data
    result=m.prepare(SOURCE,path)
    assert len(result)==10 and {r['format'] for r in result}=={'PNG','JPEG','TIFF'}

@pytest.mark.parametrize('field',['text','label','reference','expected'])
def test_no_labels(data,field):
    path,rows,save=data;rows[0][field]='not an inference input';save()
    with pytest.raises(ValueError):m.prepare(SOURCE,path)

@pytest.mark.parametrize('value',['../escape.png','/tmp/escape.png',''])
def test_path_rejection(data,value):
    path,rows,save=data;rows[0]['image']=value;save()
    with pytest.raises((ValueError,FileNotFoundError)):m.prepare(SOURCE,path)

@pytest.mark.parametrize('value',['','x'*65,'has spaces','😀'])
def test_invalid_id(data,value):
    path,rows,save=data;rows[0]['id']=value;save()
    with pytest.raises(ValueError):m.prepare(SOURCE,path)

def test_duplicate_id(data):
    path,rows,save=data;rows[1]['id']=rows[0]['id'];save()
    with pytest.raises(ValueError):m.prepare(SOURCE,path)

def test_duplicate_output_stem(data):
    path,rows,save=data;new=path.parent/'case_0.jpg';shutil.copyfile(path.parent/rows[1]['image'],new)
    rows[1]['image']=new.name;rows[1]['sha256']=m.digest(new);save()
    with pytest.raises(ValueError,match='collide'):m.prepare(SOURCE,path)

def test_input_bytes_changed(data):
    path,rows,_=data;(path.parent/rows[0]['image']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash'):m.prepare(SOURCE,path)

def test_source_bytes_changed(data,tmp_path):
    path,_,_=data;copy=tmp_path/'source';shutil.copytree(SOURCE,copy)
    (copy/'von_read/native_reader.py').write_text('raise RuntimeError("unreviewed")')
    with pytest.raises(ValueError,match='source changed'):m.prepare(copy,path)

def test_source_symlink_rejected(data,tmp_path):
    path,_,_=data;copy=tmp_path/'source';shutil.copytree(SOURCE,copy)
    file=copy/'packaging/app.py';file.unlink();file.symlink_to(SOURCE/'packaging/app.py')
    with pytest.raises(ValueError):m.prepare(copy,path)

def test_large_image_is_explicit_blocker(data):
    path,rows,save=data;p=path.parent/rows[0]['image']
    Image.new('1',(5001,4800)).save(p);rows[0]['sha256']=m.digest(p);save()
    with pytest.raises(ValueError,match='24 MP'):m.prepare(SOURCE,path)

def test_multiframe_tiff_is_explicit_blocker(data):
    path,rows,save=data;p=path.parent/rows[2]['image'];im=Image.new('RGB',(8,8))
    im.save(p,save_all=True,append_images=[im]);rows[2]['sha256']=m.digest(p);save()
    with pytest.raises(ValueError,match='multiframe'):m.prepare(SOURCE,path)

def test_three_format_coverage_required(data):
    path,rows,save=data
    for r in rows:
        p=path.parent/r['image'];Image.new('RGB',(32,24)).save(p,format='PNG');r['sha256']=m.digest(p)
    save()
    with pytest.raises(ValueError,match='coverage'):m.prepare(SOURCE,path)

@pytest.mark.parametrize('count',[0,9,11])
def test_exactly_ten(data,count):
    path,rows,save=data
    if count==11:rows.append(dict(rows[0]))
    else:del rows[count:]
    save()
    with pytest.raises(ValueError,match='exactly ten'):m.prepare(SOURCE,path)

def test_plan_is_default_no_gpu_no_output(data,tmp_path):
    path,_,_=data;out=tmp_path/'output'
    r=subprocess.run([sys.executable,str(SCRIPT),'--source',str(SOURCE),'--inputs',str(path),
                      '--model',str(tmp_path/'missing-model'),'--output',str(out)],capture_output=True,text=True,timeout=10)
    assert r.returncode==0
    result=json.loads(r.stdout)
    assert result['status']=='plan_only' and not result['gpu_execution'] and not out.exists()

def test_no_amd_refuses_execute(data,tmp_path):
    if Path('/dev/kfd').exists():pytest.skip('This guard specifically targets CPU-only hosts')
    path,_,_=data;out=tmp_path/'output'
    r=subprocess.run([sys.executable,str(SCRIPT),'--source',str(SOURCE),'--inputs',str(path),
                      '--model',str(tmp_path/'missing'),'--output',str(out),'--execute'],capture_output=True,text=True,timeout=10)
    assert r.returncode==1 and json.loads(r.stdout)['status']=='refused' and not out.exists()

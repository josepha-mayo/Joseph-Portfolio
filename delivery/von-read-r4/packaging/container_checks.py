"""Check the real /app CLI using an external authored reader, never CPU OCR."""
from __future__ import annotations
import argparse,hashlib,json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path

def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument('--app-root',type=Path,default=Path('/app'));parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    root=a.app_root.resolve();sys.path.insert(0,str(root))
    from PIL import Image
    from von_read.warm_runtime import read_ready,_supervisor_running
    assert (root/'app.py').is_file()
    results=[]
    with tempfile.TemporaryDirectory(prefix='vc-') as td:
        base=Path(td);rd=base/'r';rd.mkdir(mode=0o700);inp=base/'i';inp.mkdir();out=base/'o';out.mkdir();loads=base/'loads'
        fixture=base/'fixture.py'
        fixture.write_text("import sys,time\nfrom pathlib import Path\nfrom von_read.warm_runtime import serve,supervise\nrd,inp,loads,mode=sys.argv[1:]\nclass Reader:\n def generate(self,image,**kwargs):\n  if image.getpixel((0,0))[0]==4:return {'text':'partial','ended_eos':False,'generated_tokens':96}\n  return {'text':'fixture completed','ended_eos':True,'generated_tokens':5}\ndef factory():\n time.sleep(.8)\n with Path(loads).open('a') as f:f.write('load\\n')\n return Reader()\nif mode=='worker':serve(Path(rd),Path(inp),factory)\nelse:raise SystemExit(supervise([sys.executable,__file__,rd,inp,loads,'worker'],Path(rd),startup_seconds=10))\n")
        env={**os.environ,'PYTHONPATH':str(root)}
        worker=subprocess.Popen([sys.executable,str(fixture),str(rd),str(inp),str(loads),'supervisor'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            stop=time.monotonic()+6
            while not _supervisor_running(rd):
                if worker.poll() is not None or time.monotonic()>stop:raise RuntimeError('Fixture startup failed')
                time.sleep(.01)
            assert not (rd/'ready.json').exists(), 'Exercise a call during loading'
            for i in range(10):
                ext=['png','jpg','tiff'][i%3];image=inp/f'case.{i}.{ext}'
                Image.new('RGB',(16,16),(1,0,0)).save(image)
                start=time.monotonic()
                r=subprocess.run([sys.executable,str(root/'app.py'),'--input-image',str(image),'--runtime-dir',str(rd),'--output-dir',str(out)],cwd=root,env=env,capture_output=True,timeout=8)
                assert r.returncode==0,r.stderr.decode(errors='replace')
                assert json.loads((out/f'case.{i}_output.json').read_text())=={'text':'fixture completed'}
                results.append({'format':ext,'exit':r.returncode,'wall_seconds':time.monotonic()-start})
            assert loads.read_text().splitlines()==['load']
            assert read_ready(rd)['model_loads']==1
            bad=inp/'bad.png';Image.new('RGB',(16,16),(4,0,0)).save(bad)
            stale=out/'bad_output.json';stale.write_text('{"text":"stale"}')
            r=subprocess.run([sys.executable,str(root/'app.py'),'--input-image',str(bad),'--runtime-dir',str(rd),'--output-dir',str(out)],cwd=root,env=env,capture_output=True,timeout=5)
            assert r.returncode!=0 and not stale.exists()
            metrics=json.loads((rd/'metrics.json').read_text());assert metrics['completed_requests']==10
        finally:
            if (rd/'ready.json').exists():
                os.kill(json.loads((rd/'ready.json').read_text())['pid'],signal.SIGTERM)
            if worker.poll() is None:
                try:worker.wait(timeout=3)
                except subprocess.TimeoutExpired:worker.terminate();worker.wait(timeout=3)
            if worker.stderr:worker.stderr.close()
    report={'status':'passed','scope':'Real application CLI inside image; authored reader fixture, not GPU OCR','checks':{'ten_separate_cli_calls':True,'one_reader_load':True,'PNG_JPEG_TIFF':True,'cold_start_race':True,'incomplete_and_stale_output_rejected':True},'calls':results,'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'von_read').glob('*.py')},'gpu_inference':False}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('calls','source_sha256')}))
if __name__=='__main__':main()

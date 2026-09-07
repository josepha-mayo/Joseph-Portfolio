#!/usr/bin/env python3
"""Add Replay Desk without replacing the submitted v0.1 artifact."""
from pathlib import Path
import shutil,subprocess,sys
R=Path(__file__).resolve().parents[1];U=R/'upgrade02';O=R/'v02';O.mkdir(exist_ok=True)
subprocess.run([sys.executable,str(R/'build.py')],cwd=R,check=True)
s=(R/'index.html').read_text();a,b=s.rsplit('</body>',1)
extras='\n'.join('<script>'+ (U/n).read_text().replace('</script','<\\/script')+'</script>' for n in ['replay.js','replay-ui.js'])
(O/'index.html').write_text(a+extras+'</body>'+b)
(O/'evidence').mkdir(exist_ok=True)
for n in ['LICENSE'] :shutil.copyfile(R/n,O/n)
(O/'examples').mkdir(exist_ok=True);shutil.copyfile(R/'examples/scenario.json',O/'examples/scenario.json')

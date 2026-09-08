"""Package only an executed current release; historical evidence remains labelled."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,zipfile,shutil
R=Path(__file__).resolve().parents[1];P=R/'public';E=R/'evidence'
release=json.loads((E/'desk-release.json').read_text());context=json.loads((E/'desk-context-browser.json').read_text());demo=json.loads((E/'desk-demo.json').read_text())
assert all(r['status']=='passed' for r in [release,context,demo])
assert hashlib.sha256((R/'vendor/core.cjs').read_bytes()).hexdigest()=='bbb1c78f2b77a6ab9ec47792b41bdec842c703c5ebf08014a5c53b80d072e1ff'
assert hashlib.sha256((R/'vendor/model.json').read_bytes()).hexdigest()=='83d562317236464ea09c357522184efe83704746362a6434337b6f570fd64381'
report={'status':'passed','generated_at':datetime.now(timezone.utc).isoformat(),'node_tests':release['node_tests'],'browser_workflows':release['inherited_browser_workflows']+release['new_browser_workflows']+context['count'],'browser_breakdown':{'inherited':release['inherited_browser_workflows'],'repair_desk':release['new_browser_workflows'],'report_context':context['count']},'demo_seconds':demo['demo_seconds'],'audio_rms':demo['audio_rms'],'narration':demo['narration'],'scope':'Internal actual MCP and browser checks using synthetic equations, not a learner study. Exact evaluator, learned weights and event scoring unchanged; report question metadata added. No live Alexa, language-model host or AWS runtime claim.'}
(E/'desk-publish.json').write_text(json.dumps(report,indent=2))
(P/'evidence').mkdir(exist_ok=True)
for f in E.glob('desk*'):
 if f.is_file():shutil.copy2(f,P/'evidence'/f.name)
# No generated archives/media/recursive hash manifests inside the source archive.
with zipfile.ZipFile(P/'desk-source.zip','w',zipfile.ZIP_DEFLATED)as z:
 for f in sorted(R.rglob('*')):
  rel=f.relative_to(R)
  if not f.is_file() or any(n in rel.parts for n in ['node_modules','.git','upgrade','__pycache__']):continue
  if f.suffix in ['.mp4','.webm','.wav','.mp3','.xz','.zip'] and str(rel)!='vendor/original-counterstep-source.zip':continue
  if f.name in ['release-files.json','desk-files.json','desk-release-files.json']:continue
  z.write(f,str(rel))
shutil.copy2(P/'desk-source.zip',P/'source.zip')
names=['index.html','app.js','style.css','repair-desk.mjs','judge.html','README.md','LICENSE','SKILL.md','demo.mp4','demo-transcript.md','desk-source.zip','source.zip','evidence/desk-publish.json','evidence/desk-demo.json']
manifest={name:{'sha256':hashlib.sha256((P/name).read_bytes()).hexdigest(),'bytes':(P/name).stat().st_size}for name in names}
(P/'desk-release-files.json').write_text(json.dumps(manifest,indent=2))
# The original filenames now describe the current release, avoiding stale source/demo hashes.
(P/'release-files.json').write_text(json.dumps(manifest,indent=2));(P/'desk-files.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(report))

from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
s=(R/'src/page.html').read_text()
s=s.replace('</head>','<style>'+(R/'src/layout.css').read_text()+'</style></head>')
core=(R/'src/core.js').read_text()
s=s.replace('<!-- CORE -->','<script id="coreSource">'+core+'</script>')
s=s.replace('<!-- WORKER -->',(R/'src/worker.js').read_text())
s=s.replace('<!-- DEMO -->',json.dumps({'old':(R/'examples/vendor-ipv4.csv').read_text(),'next':(R/'examples/synthetic-candidate.csv').read_text(),'traffic':(R/'examples/traffic.csv').read_text()}).replace('</','<\\/'))
s=s.replace('<!-- APP -->','<script>'+(R/'src/app.js').read_text()+'</script>')
(R/'index.html').write_text(s)
print('Built',len(s.encode()),'bytes')

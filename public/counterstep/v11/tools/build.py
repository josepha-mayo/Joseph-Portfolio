from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=(R/'src/page.html').read_text().replace('<!-- CORE -->','<script>'+ (R/'src/core.js').read_text()+'\n'+(R/'src/hash.js').read_text()+'</script>').replace('<!-- MODEL -->',(R/'src/model.json').read_text().replace('</','<\\/')).replace('<!-- APP -->','<script>'+(R/'src/app.js').read_text()+'</script>')
(R/'index.html').write_text(s)
print('Built Counterstep:',len(s.encode()),'bytes')

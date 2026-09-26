from pathlib import Path
import subprocess,sys,hashlib,json
R=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,'tools/build.py'],cwd=R,check=True)
s=(R/'src/path-page.html').read_text().replace('<!-- CORE -->','<script>'+(R/'src/core.js').read_text()+'\n'+(R/'src/hash.js').read_text()+'</script>').replace('<!-- MODEL -->',(R/'src/model.json').read_text().replace('</','<\\/')).replace('<!-- PATH -->','<script>'+(R/'src/path.js').read_text()+'</script>').replace('<!-- UI -->','<script>'+(R/'src/path-ui.js').read_text()+'</script>')
assert '<!-- PATH -->' not in s and '<!-- UI -->' not in s
(R/'path.html').write_text(s)
print('Transfer Path built:',len(s.encode()),'bytes. Original classic app retained.')

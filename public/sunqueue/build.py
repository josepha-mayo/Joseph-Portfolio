#!/usr/bin/env python3
"""Build the original local-first SunQueue application from its published source."""
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parent
expected={
 'src/app.js':'d1eb902dcb07142c407dc16b323089f716914722884dee094ae5c396bf7c1867',
 'src/core.js':'d716789fed25a7eedb67407ecd81256e0cf0e6131e18b69d0f0fb0af62dd365e',
 'src/index.html':'fc02466ddd6f98d6380ad86c653351a97a174d17f285a4a594b294d3068008ed',
 'examples/scenario.json':'f48652a5de1665e468341f936ea82d78d95d53423c14d1cb9bfeec6d41813a42',
}
for path,digest in expected.items():
 actual=hashlib.sha256((root/path).read_bytes()).hexdigest()
 if actual!=digest:raise ValueError(f'Published source differs from tested local revision: {path}: {actual}')
text=(root/'src/index.html').read_text()
for marker,file in [('/*CORE*/','src/core.js'),('/*APP*/','src/app.js'),('/*EXAMPLE*/','examples/scenario.json')]:
 content=(root/file).read_text().replace('</script','<\\/script')
 assert text.count(marker)==1
 text=text.replace(marker,content)
(root/'index.html').write_text(text)
(root/'evidence').mkdir(exist_ok=True)
print('Built',root/'index.html',len(text.encode()),'bytes')

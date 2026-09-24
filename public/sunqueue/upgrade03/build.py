#!/usr/bin/env python3
"""Build Shift Sheet alongside the unchanged original and v0.2 sources."""
from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parents[1];U=R/'upgrade03';O=R/'v03';O.mkdir(exist_ok=True)
# Never update the original core just to make a regression disappear.
assert hashlib.sha256((R/'src/core.js').read_bytes()).hexdigest()=='d716789fed25a7eedb67407ecd81256e0cf0e6131e18b69d0f0fb0af62dd365e'
text=(R/'src/index.html').read_text()
for marker,p in [('/*CORE*/',R/'src/core.js'),('/*APP*/',U/'app.js'),('/*EXAMPLE*/',R/'examples/scenario.json')]:
 assert text.count(marker)==1;text=text.replace(marker,p.read_text().replace('</script','<\\/script'))
text=text.replace('</style>','\n'+(U/'shift.css').read_text()+'</style>',1)
text=text.replace('<title>SunQueue | Work with the daylight.</title>','<title>SunQueue Shift Sheet | Same work, honest comparison.</title>')
text=text.replace('Schedule flexible jobs around solar supply, outages and deadlines. Compare the same work against an early-start baseline, then stress-test the plan.','Plan the same work around daylight. Take clock-time work cards with you, then check reported runs without hiding stopped jobs or extra battery use.')
text=text.replace('<div id="notice"','<nav class="op-nav" aria-label="Workday sections"><a href="#jobBuilder">1. Enter work</a><a href="#solve">2. Plan</a><a href="#shiftDesk">3. Shift sheet and run log</a><a href="#replayDesk">4. Fixed-plan replay</a></nav><div id="notice"',1)
text=text.replace('SunQueue 0.1.0 /','SunQueue Shift Sheet 0.3.0 /')
extra='\n'.join('<script>'+p.read_text().replace('</script','<\\/script')+'</script>' for p in [R/'upgrade02/replay.js',U/'replay-ui.js',U/'shift.js',U/'shift-ui.js'])
text=text.replace('</body>',extra+'</body>');(O/'index.html').write_text(text)
for d in ['evidence','examples']:(O/d).mkdir(exist_ok=True)
shutil.copyfile(R/'LICENSE',O/'LICENSE');shutil.copyfile(R/'examples/scenario.json',O/'examples/scenario.json')
print('Built Shift Sheet',len(text.encode()),'bytes')
for name in ['README.md','judge.html']:shutil.copyfile(U/name,O/name)

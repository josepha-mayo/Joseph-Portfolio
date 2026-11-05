#!/usr/bin/env python3
"""Build a self-contained browser app, with original demo media embedded."""
import base64, json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def js_json(x):
    return json.dumps(x,ensure_ascii=False).replace('</','<\\/')
assets='window.CUTPROOF_DEMO='+js_json({
 'cues':json.loads((root/'examples/source.cues.json').read_text()),
 'media':'data:video/mp4;base64,'+base64.b64encode((root/'examples/source.mp4').read_bytes()).decode()
})+';\nwindow.CUTPROOF_RENDERER='+js_json((root/'scripts/render.py').read_text())+';'
html=(root/'src/index.html').read_text()
for token,content in [('/*__CORE__*/',(root/'src/core.js').read_text()),('/*__WORKFLOW__*/',(root/'src/workflow.js').read_text()),('/*__ASSETS__*/',assets),('/*__APP__*/',(root/'src/app.js').read_text())]:
 html=html.replace(token,content)
(root/'cutproof.html').write_text(html,encoding='utf-8')
(root/'web/index.html').write_text(html,encoding='utf-8')
print(f'Built standalone app: {len(html.encode()):,} bytes')

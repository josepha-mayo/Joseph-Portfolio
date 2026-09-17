"""Build a separate v15 candidate; never edit v13, v14, or submission metadata."""
from pathlib import Path
import argparse, hashlib, json, shutil
p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
U=Path(__file__).resolve().parent;R=U.parent
B=a.source or R/'public/cutproof/v14';O=a.output or R/'public/cutproof/v15'
assert B.exists() and B.resolve()!=O.resolve()
if O.exists():shutil.rmtree(O)
shutil.copytree(B,O,ignore=shutil.ignore_patterns('source.zip','candidate-files.json','__pycache__','*.pyc'))
# Keep historical release evidence separate from current execution reports.
if (O/'evidence').exists():(O/'evidence').rename(O/'evidence-v14')
(O/'evidence').mkdir();shutil.copy2(U/'passages.js',O/'passages.js')
s=(O/'desk.js').read_text();start=s.index('function showRelated(){');end=s.index("$('evSearch').onclick",start)
s=s[:start]+(U/'desk-replacement.js').read_text()+s[end:]
s=s.replace('CHECK WORDS. SEARCH BEYOND THE CUT.', 'PASSAGE REPAIR / CANDIDATE 1.5')
s=s.replace('BM25 lexical retrieval, with framing-word cues.', 'BM25 lexical retrieval with surrounding source cues. Matching wording and neighboring context are labelled separately.')
(O/'desk.js').write_text(s)
h=(O/'index.html').read_text();needle='<script src="evidence.js"></script><script src="desk.js"></script>';assert h.count(needle)==1
h=h.replace(needle,'<script src="evidence.js"></script><script src="passages.js"></script><script src="desk.js"></script>',1)
# Visible candidate identity, without rewriting the independently versioned Source Lock schema.
h=h.replace('</head>','<meta name="cutproof-candidate" content="1.5.0-passage-context"></head>',1)
(O/'index.html').write_text(h)
(O/'PASSAGE-CANDIDATE.md').write_text((U/'README.md').read_text())
unchanged=['evidence.js','binding.js','source-lock.js','render.py','speech-worker.mjs']
for f in unchanged:assert (B/f).read_bytes()==(O/f).read_bytes(),f
(O/'evidence/build.json').write_text(json.dumps({'candidate':'1.5.0-passage-context','unchanged_modules':unchanged,'original_entry_changed':False,'scope':'Source-neighborhood review and contiguous range repair, not a new ranker or boundary-risk detector.'},indent=2))
print(O)

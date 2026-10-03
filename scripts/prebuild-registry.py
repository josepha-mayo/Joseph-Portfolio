"""Choose a registry prebuild path without changing production semantics."""
from __future__ import annotations
import os,subprocess,sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
preview=os.environ.get('CONTEXT')=='deploy-preview' or os.environ.get('VON_V3_PREVIEW')=='1'
scripts=['prepare-von-registry.py','prepare-von-registry-r35.py','prepare-von-registry-r61.py']
if preview:
    subprocess.check_call([sys.executable,str(root/'scripts/prepare-von-registry-preview.py')],cwd=root)
else:
    for name in scripts:
        subprocess.check_call([sys.executable,str(root/'scripts'/name)],cwd=root)

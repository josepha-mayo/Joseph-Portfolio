"""Private bounded worker; all input/output files are in the parent's job directory."""
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'engine'))
import cv2
from evidence_workflow import execute
from review_prepare import prepare

def main():
    p=Path(sys.argv[1]).resolve()
    cv2.setNumThreads(2)
    result=execute(p,json.loads((p/'manifest.json').read_text()))
    (p/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    prepare(p,p/'report.json',p/'review.html')
if __name__=='__main__':main()

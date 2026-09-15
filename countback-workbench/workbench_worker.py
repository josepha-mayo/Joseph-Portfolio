"""Private bounded worker; all input/output files are in the parent's job directory."""
from pathlib import Path
import json, os, sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'engine'))
import cv2
from evidence_workflow import execute
from review_prepare import prepare

def main():
    p=Path(sys.argv[1]).resolve()
    cv2.setNumThreads(2)
    result=execute(p,json.loads((p/'manifest.json').read_text()))
    if os.environ.get('COUNTBACK_POSE_REVIEW') == '1':
        sys.path.insert(0,str(ROOT.parent/'countback-validation'))
        from pose_refine import refine
        from pose_view_policy import apply_review_policy
        result=apply_review_policy(refine(p,result))
    (p/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    prepare(p,p/'report.json',p/'review.html')
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Inspect Joseph's supplied five-photo development set without retaking pictures.

The manifest selects reference-only object rectangles. Scene locations are never
supplied to the matcher. Default execution requires OpenCV 5; a diagnostic on 4.x
must explicitly opt in. No remote service, output overwrite or public upload.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import time
import cv2 as cv
import numpy as np
from PIL import Image,ImageOps
from practical_inspection import PracticalInspection


def load_photo(root:Path,name:str)->tuple[np.ndarray,dict]:
    if not isinstance(name,str) or len(name)>200 or Path(name).name!=name:
        raise ValueError('Photo must be a basename inside the selected directory.')
    full=(root/name).resolve()
    if not full.is_relative_to(root.resolve()) or not full.is_file() or full.stat().st_size>20_000_000:
        raise ValueError('Missing or oversized photo: '+name)
    raw=full.read_bytes()
    with Image.open(BytesIO(raw)) as image:
        if image.format not in ('JPEG','PNG') or image.width*image.height>12_000_000:
            raise ValueError('Expected a JPEG/PNG under 12 million pixels.')
        rgb=ImageOps.exif_transpose(image).convert('RGB')
    return np.asarray(rgb)[:,:,::-1].copy(),{'filename':name,'sha256':sha256(raw).hexdigest(),'decoded_size':list(rgb.size)}


def execute(directory:Path,manifest:dict,*,development_runtime:bool=False)->dict:
    if not cv.__version__.startswith('5.') and not development_runtime:
        raise ValueError('Installed OpenCV '+cv.__version__+' is not 5.x. Use --development-runtime only for a labelled diagnostic.')
    if set(manifest)!={'schema','references','views'} or manifest['schema']!='countback-reference-rois-1':
        raise ValueError('Invalid manifest.')
    if not isinstance(manifest['references'],dict) or not 1<=len(manifest['references'])<=12:
        raise ValueError('Provide 1 to 12 reference records.')
    if not isinstance(manifest['views'],list) or not 1<=len(manifest['views'])<=3:
        raise ValueError('Provide 1 to 3 supplied scene photos.')
    refs={};provenance={}
    for name,spec in manifest['references'].items():
        if set(spec)!={'filename','roi_fraction'}:raise ValueError('Invalid reference specification.')
        image,info=load_photo(directory,spec['filename']);height,width=image.shape[:2]
        b=spec['roi_fraction']
        if not isinstance(b,list) or len(b)!=4 or not all(type(n) in (int,float) and np.isfinite(n) for n in b):
            raise ValueError('Invalid reference rectangle.')
        if not 0<=b[0]<b[2]<=1 or not 0<=b[1]<b[3]<=1:
            raise ValueError('Reference rectangle must lie inside the photograph.')
        x0,y0,x1,y1=round(b[0]*width),round(b[1]*height),round(b[2]*width),round(b[3]*height)
        if min(x1-x0,y1-y0)<24:raise ValueError('Reference crop too small.')
        refs[name]=image[y0:y1,x0:x1].copy();provenance[name]={**info,'reference_only_roi_xyxy':[x0,y0,x1,y1]}
    session=PracticalInspection(refs,max_views=len(manifest['views']));start=time.monotonic()
    for index,name in enumerate(manifest['views'],1):
        image,info=load_photo(directory,name);provenance['view-'+str(index)]=info
        result=session.observe(image,'view-'+str(index))
        if not result['accepted']:raise ValueError('Rejected view: '+result['reason'])
    report=session.report()
    report.update(created_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=round(time.monotonic()-start,3),
                  input_provenance=provenance,manual_annotations='Reference-only rectangles, not scene locations or correspondence labels.',
                  physical_count_attestation='Not requested or fabricated; photos are used as a development diagnostic.',
                  user_photos_edited_for_inference=False,reference_crops_derived_locally=True,
                  model_images_generated=False,public_image_permission_assumed=False)
    return report


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--photos',type=Path,required=True)
    p.add_argument('--manifest',type=Path,default=Path(__file__).parent/'real-photo-set.json')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-local-photo-analysis',action='store_true')
    p.add_argument('--development-runtime',action='store_true')
    a=p.parse_args()
    try:
        if not a.allow_local_photo_analysis:raise ValueError('Local analysis authorization is required.')
        if a.output.exists():raise ValueError('Output exists; evidence is not overwritten.')
        if not a.manifest.is_file() or a.manifest.stat().st_size>100_000:raise ValueError('Missing or oversized manifest.')
        cv.setNumThreads(2)
        report=execute(a.photos,json.loads(a.manifest.read_text()),development_runtime=a.development_runtime)
        with a.output.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
        print(json.dumps({'parts':report['parts'],'runtime':report['opencv_version'],'seconds':report['elapsed_seconds']},indent=2))
        return 0
    except (ValueError,OSError,cv.error,Image.DecompressionBombError) as error:
        print('NOT COMPLETE: '+str(error));return 2

if __name__=='__main__':raise SystemExit(main())

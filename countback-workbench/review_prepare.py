#!/usr/bin/env python3
"""Create a private, self-contained operator review from existing engine evidence.

No image is uploaded. Display copies hide booklet printing; input pixels and the
matching engine remain untouched. Scene regions come from engine output only.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,math,sys
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT=Path(__file__).resolve().parent
NAMES={'booklet':'Booklet','remote':'Remote control','mouse':'Gaming mouse'}
LABELS={'geometric_patch_support':'LANDMARK SUPPORT','internal_pattern_consistent':'PATTERN AGREEMENT','appearance_only':'APPEARANCE ONLY','ambiguous':'AMBIGUOUS','unresolved':'UNRESOLVED'}
def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def image(path:Path)->Image.Image:
    if path.stat().st_size>20_000_000:raise ValueError('Oversized photo')
    with Image.open(path) as im:
        if im.format not in {'JPEG','PNG'} or im.width*im.height>12_000_000:raise ValueError('Unsupported image')
        return ImageOps.exif_transpose(im).convert('RGB')
def uri(im:Image.Image,max_side:int=880)->str:
    im=im.copy();im.thumbnail((max_side,max_side))
    b=BytesIO();im.save(b,format='JPEG',quality=88,optimize=True)
    return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
def find_poly(v:dict,name:str):
    detail=v['parts'][name]
    if detail.get('polygon'):return detail['polygon']
    options=(detail.get('geometric_review',{}).get('appearance') or {}).get('candidates',[])
    return options[0]['polygon'] if options else None

def prepare(photos:Path,result:Path,output:Path)->dict:
    if output.exists():raise ValueError('Output exists; choose a new path')
    if not result.is_file() or result.stat().st_size > 5_000_000:raise ValueError('Missing or oversized evidence file')
    raw=result.read_bytes();r=json.loads(raw)
    if r.get('schema')!='countback-evidence-workflow-0.4' or not r.get('opencv5_executed'):raise ValueError('Expected executed OpenCV 5 evidence')
    if not 1<=len(r.get('parts',{}))<=12 or not 1<=len(r.get('views',[]))<=3:raise ValueError('Invalid review scope')
    originals={}
    for label,info in r['input_provenance'].items():
        name=info['filename'];path=(photos/name).resolve()
        if Path(name).name!=name or not path.is_relative_to(photos.resolve()):raise ValueError('Photo path outside selected directory')
        if sha(path.read_bytes())!=info['sha256']:raise ValueError('Photo changed since inference: '+label)
        im=image(path)
        if list(im.size)!=info['decoded_size']:raise ValueError('Image coordinate size changed')
        originals[label]=im
    displays={k:v.copy() for k,v in originals.items()}
    # Privacy masks are display-only. No text is read or used as a semantic label.
    if 'booklet' in displays:
        roi=r['input_provenance']['booklet']['reference_only_roi_xyxy']
        ImageDraw.Draw(displays['booklet']).rectangle(roi,fill='#253246')
        for v in r['views']:
            poly=find_poly(v,'booklet')
            if poly:
                dr=ImageDraw.Draw(displays[v['label']]);dr.polygon([tuple(p) for p in poly],fill='#253246')
    items=[]
    for name,part in r['parts'].items():
        ri=r['input_provenance'][name];ref=displays[name].crop(tuple(ri['reference_only_roi_xyxy']));views=[]
        for v in r['views']:
            poly=find_poly(v,name);im=displays[v['label']].copy();w,h=im.size
            if poly:
                if len(poly)<3 or any(not math.isfinite(float(z)) for p in poly for z in p):raise ValueError('Invalid evidence polygon')
                x=[p[0] for p in poly];y=[p[1] for p in poly];pad=max(25,.18*max(max(x)-min(x),max(y)-min(y)))
                bbox=[max(0,math.floor(min(x)-pad)),max(0,math.floor(min(y)-pad)),min(w,math.ceil(max(x)+pad)),min(h,math.ceil(max(y)+pad))]
                if bbox[0]>=bbox[2] or bbox[1]>=bbox[3]:raise ValueError('Evidence crop outside image')
                clipped=any(a<0 or a>=w or b<0 or b>=h for a,b in poly)
                dr=ImageDraw.Draw(im);dr.line([tuple(p) for p in poly]+[tuple(poly[0])],fill='#47e1bb',width=4)
                crop=im.crop(tuple(bbox));caption='Engine-proposed region, with surrounding pixels. '+('Proposal extends outside this photograph. ' if clipped else '')
            else:
                bbox=[0,0,w,h];crop=im;caption='No candidate region was supported. Full photograph shown. '
            caption+='Printing hidden in the booklet display; inference used original images.' if name=='booklet' else 'A visual judgment does not establish a unique physical instance.'
            views.append({'id':v['label'],'label':v['label'].replace('view-','Photo '),'image_sha256':r['input_provenance'][v['label']]['sha256'],
              'region':{'polygon':poly,'display_crop_xyxy':bbox,'display_only':True},'crop':uri(crop),'context':uri(im,1100),'caption':caption})
        level=part['evidence_level']
        supported=part.get('geometric_views',[]) or part.get('pattern_views',[])
        locations=', '.join(supported) if supported else 'no supported view'
        detail={
            'geometric_patch_support':f'Corresponding local landmarks support a reference patch in {locations}. This does not establish a unique physical instance.',
            'internal_pattern_consistent':f'Internal-layout agreement was found in {locations}. Similar manufactured objects may share the same pattern.',
            'appearance_only':'Only colour/outline resemblance was found. Automation has not verified this reference. Inspect the available photographs.',
            'ambiguous':'Competing references or candidates remain ambiguous. Do not treat them as separately identified physical items.',
            'unresolved':'No supported correspondence was obtained from the processed photographs. This does not prove absence.'
        }.get(level,'Inspect the evidence and record what is and is not visible.')
        if name=='booklet':detail+=' Printing is concealed in the display copy; inference used original pixels.'
        items.append({'id':name,'title':NAMES.get(name,name),'evidence_level':level,'evidence_label':LABELS.get(level,level),'identity_verified':False,
          'evidence_detail':detail,'instruction':'Compare the reference and candidate, then record a reasoned assessment. Leave it unclear when the image is insufficient.',
          'reference_image':uri(ref),'reference_image_sha256':ri['sha256'],'reference_note':'Reference-only crop. Booklet printing is hidden in display copies.' if name=='booklet' else 'Crop from your separately supplied reference photograph.',
          'suggested_view':(part.get('suggested_review_region') or {}).get('view',views[0]['id']),'views':views})
    c={'schema':'countback-review-case-1','evidence_sha256':sha(raw),'opencv_version':r['opencv_version'],'input_provenance':r['input_provenance'],'trace':r['trace'],'items':items,
       'display_redactions':'Booklet printing concealed in display copies only. No raw photo data is exported in the handoff.','aws_executed':False,'physical_kit_holdout':False}
    js=lambda name:(ROOT/'app'/name).read_text()
    data=json.dumps(c,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    html=js('template.html').replace('__CASE_DATA__',data).replace('__STATE_JS__',js('review_state.js')).replace('__UI_JS__',js('ui.js')).replace('__REFERENCE_COUNT__',str(len(items))).replace('__OBSERVATION_COUNT__',str(len(r['views'])))
    with output.open('x',encoding='utf-8') as stream:stream.write(html)
    return c
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--photos',type=Path,required=True);p.add_argument('--result',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:prepare(a.photos,a.result,a.output);print(a.output)
    except (ValueError,OSError,KeyError) as exc:print('NOT BUILT: '+str(exc),file=sys.stderr);raise SystemExit(2)

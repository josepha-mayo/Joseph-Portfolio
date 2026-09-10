"""Evidence-driven inspection of already supplied photographs, with bounded actions.

No camera control, future-view scoring, LLM, AWS call, or physical count. The
controller only opens the next supplied image when current visual evidence leaves
an unresolved reference. Every automated check still ends in operator review.
"""
from __future__ import annotations
from copy import deepcopy
from itertools import combinations
from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone
import time
import json
import cv2 as cv
import numpy as np
from practical_inspection import PracticalInspection
from src.structure import check_structure
from src.joint import outline_overlap
from run_supplied_set import load_photo

VISUALLY_SUPPORTED={'geometric_patch_support','internal_pattern_consistent'}

class EvidenceWorkflow:
    def __init__(self,references:dict[str,np.ndarray],max_views:int=3):
        self.base=PracticalInspection(references,max_views=max_views)
        self.views=[]

    def observe(self,image:np.ndarray,label:str)->dict:
        raw=self.base.observe(image,label)
        if not raw['accepted']:return raw
        current={'label':label,'image_sha256':raw['image_sha256'],'parts':{},'conflicts':deepcopy(raw['conflicts'])}
        for name,part in raw['parts'].items():
            structure=None;level=part['evidence_level'];poly=part.get('polygon') if level=='geometric_patch_support' else None
            if level=='appearance_only':
                structure=check_structure(self.base.references[name],image,proposal=part['appearance'])
                if structure['status']=='internal_pattern_consistent':level='internal_pattern_consistent';poly=structure['polygon']
                elif structure['status']=='ambiguous_pattern_candidates':level='ambiguous'
            current['parts'][name]={'evidence_level':level,'polygon':poly,'geometric_review':part,'structure':structure,
                'identity_verified':False,'physical_quantity':None,'condition':'not_assessed'}
        # Different labels cannot turn one supported footprint into two items.
        for a,b in combinations(current['parts'],2):
            x,y=current['parts'][a],current['parts'][b]
            if x['evidence_level'] in VISUALLY_SUPPORTED and y['evidence_level'] in VISUALLY_SUPPORTED:
                overlap=outline_overlap(x['polygon'],y['polygon'])
                if overlap>=.60:current['conflicts'].append({'references':[a,b],'smaller_outline_overlap':overlap,'reason':'supported_footprints_overlap_not_independent_items'})
        contested={n for c in current['conflicts'] for n in c['references']}
        for name in contested:current['parts'][name]['evidence_level']='ambiguous'
        self.views.append(deepcopy(current))
        return {'accepted':True,**deepcopy(current)}

    def snapshot(self)->dict:
        contested={n for group in self.base.aliases for n in group}
        contested.update(n for v in self.views for c in v['conflicts'] for n in c['references'])
        parts={}
        for name in self.base.references:
            geo=[v['label'] for v in self.views if v['parts'][name]['evidence_level']=='geometric_patch_support']
            pattern=[v['label'] for v in self.views if v['parts'][name]['evidence_level']=='internal_pattern_consistent']
            candidates=[v['label'] for v in self.views if v['parts'][name]['evidence_level']=='appearance_only']
            local_ambiguous=any(v['parts'][name]['evidence_level']=='ambiguous' for v in self.views)
            level='ambiguous' if name in contested or local_ambiguous else 'geometric_patch_support' if geo else 'internal_pattern_consistent' if pattern else 'appearance_only' if candidates else 'unresolved'
            review_options=[]
            for view in self.views:
                detail=view['parts'][name]
                if detail['evidence_level'] in VISUALLY_SUPPORTED:
                    review_options.append({'view':view['label'],'polygon':detail['polygon'],'clipped':False,'priority':0,'reason':'inspect_supported_visual_evidence'})
                for candidate in (detail['geometric_review'].get('appearance') or {}).get('candidates',[]):
                    clipped=candidate['proposal_at_frame_edge']
                    review_options.append({'view':view['label'],'polygon':candidate['polygon'],'clipped':clipped,'priority':2 if clipped else 1,'reason':'appearance_only_not_identity'})
            review_options.sort(key=lambda row:(row['priority'],row['view']))
            selected=deepcopy(review_options[0]) if review_options else None
            if selected is not None:selected.pop('priority')
            parts[name]={'evidence_level':level,'geometric_views':geo,'pattern_views':pattern,'candidate_views':candidates,
                         'suggested_review_region':selected,
                         'identity_verified':False,'physical_quantity':None,'condition':'not_assessed'}
        return {'parts':parts,'distinct_views':len(self.views),'views':deepcopy(self.views),
                'identity_verified':False,'kit_complete':None,'quantity_established':False,'absence_verdict':None,
                'human_review_required':True}


def next_action(snapshot:dict,remaining:int)->dict:
    if type(remaining) is not int or not 0<=remaining<=3:raise ValueError('Invalid remaining-view budget')
    unresolved=[n for n,p in snapshot['parts'].items() if p['evidence_level'] not in VISUALLY_SUPPORTED]
    if unresolved and remaining:
        return {'action':'inspect_next_supplied_view','priority_references':unresolved,
                'reason':'current_visual_evidence_leaves_unresolved_references','camera_recapture_requested':False}
    return {'action':'operator_review','unresolved_references':unresolved,'camera_recapture_requested':False,
            'reason':'available_view_budget_exhausted' if unresolved else 'visual_evidence_available_but_no_automatic_approval'}


def execute(photos:Path,manifest:dict,*,development_runtime:bool=False)->dict:
    if not cv.__version__.startswith('5.') and not development_runtime:raise ValueError('Actual OpenCV 5 required; development mode must be explicit.')
    if not isinstance(manifest,dict) or set(manifest)!={'schema','references','views'} or manifest['schema']!='countback-reference-rois-1':raise ValueError('Invalid runtime manifest; evaluation labels are not inputs.')
    if not isinstance(manifest['references'],dict) or not 1<=len(manifest['references'])<=12:raise ValueError('Invalid reference count')
    if not isinstance(manifest['views'],list) or not 1<=len(manifest['views'])<=3:raise ValueError('Use at most three supplied views')
    refs={};provenance={}
    for name,spec in manifest['references'].items():
        if not isinstance(spec,dict) or set(spec)!={'filename','roi_fraction'}:raise ValueError('Only reference filenames and reference rectangles allowed')
        image,info=load_photo(photos,spec['filename']);h,w=image.shape[:2];b=spec['roi_fraction']
        if not isinstance(b,list) or len(b)!=4 or not all(type(x) in (float,int) and np.isfinite(x) for x in b):raise ValueError('Invalid reference crop')
        if not 0<=b[0]<b[2]<=1 or not 0<=b[1]<b[3]<=1:raise ValueError('Crop outside reference')
        x0,y0,x1,y1=np.rint(np.array(b)*[w,h,w,h]).astype(int)
        refs[name]=image[y0:y1,x0:x1].copy();provenance[name]={**info,'reference_only_roi_xyxy':[int(x0),int(y0),int(x1),int(y1)]}
    workflow=EvidenceWorkflow(refs,max_views=len(manifest['views']));trace=[];begin=time.monotonic()
    # A future observation is not loaded, scored, or inspected before this decision.
    decision={'action':'inspect_initial_supplied_view','priority_references':list(refs)}
    for index,filename in enumerate(manifest['views'],1):
        if decision['action']=='operator_review':break
        image,info=load_photo(photos,filename);provenance['view-'+str(index)]=info
        observation=workflow.observe(image,'view-'+str(index))
        if not observation['accepted']:raise ValueError('Rejected observation: '+observation['reason'])
        snapshot=workflow.snapshot();decision_after=next_action(snapshot,len(manifest['views'])-index)
        trace.append({'step':index,'decision_before':decision,'executed_action':'inspect_existing_photo','input_sha256':info['sha256'],
                      'observation_label':observation['label'],'evidence_after':{n:p['evidence_level'] for n,p in snapshot['parts'].items()},'decision_after':decision_after})
        decision=decision_after
    return {'schema':'countback-evidence-workflow-0.4',**workflow.snapshot(),
       'trace':trace,'next_action':decision,'elapsed_seconds':round(time.monotonic()-begin,3),
       'created_at':datetime.now(timezone.utc).isoformat(),'input_provenance':provenance,
       'opencv_version':cv.__version__,'opencv5_executed':cv.__version__.startswith('5.'),
       'aws_executed':False,'images_uploaded':False,'development_only':True,'physical_kit_holdout':False,
       'competition_submission_ready':False,'manual_annotations':'Existing reference-only rectangles. No scene positions or correspondence labels.',
       'scope':'Bounded deterministic controller; visual output changes whether the next supplied image is processed. Not camera control or best-view search. Interior pattern is a separate evidence tier, not a new landmark match or proof of a unique physical object.'}

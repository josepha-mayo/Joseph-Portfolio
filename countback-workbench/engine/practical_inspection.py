"""Use the images already available, with graded evidence and no camera request.

A bounded, local development adapter around the retained strict matcher.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any
import cv2 as cv
import numpy as np
from src.countback import Config, validate, fingerprint
from src.robust_matcher import inspect as low_light_inspect
from src.appearance import propose
from src.joint import JointConfig, review_results

class PracticalInspection:
    def __init__(self, references:dict[str,np.ndarray], max_views:int=2):
        if not isinstance(references,dict) or not 1<=len(references)<=12:
            raise ValueError('Supply 1 to 12 references.')
        if type(max_views) is not int or not 1<=max_views<=3:
            raise ValueError('View budget must be 1 to 3.')
        if any(not isinstance(k,str) or not k or len(k)>80 for k in references):
            raise ValueError('Invalid reference label.')
        for image in references.values():
            validate(image,Config())
            if image.ndim!=3 or image.shape[2]!=3:
                raise ValueError('BGR references required.')
        self.references={k:v.copy() for k,v in references.items()}
        self.max_views=max_views;self.views=[];self.matcher_config=Config()
        by_hash={}
        for name,image in references.items():by_hash.setdefault(fingerprint(image),[]).append(name)
        self.aliases=[names for names in by_hash.values() if len(names)>1]

    def observe(self,image:np.ndarray,label:str)->dict[str,Any]:
        validate(image,self.matcher_config)
        if image.ndim!=3 or image.shape[2]!=3:raise ValueError('BGR scene required.')
        if not isinstance(label,str) or not label or len(label)>120:raise ValueError('Invalid view label.')
        digest=fingerprint(image)
        if any(v['image_sha256']==digest for v in self.views):
            return {'accepted':False,'reason':'duplicate_pixels'}
        if digest in {fingerprint(r) for r in self.references.values()}:
            return {'accepted':False,'reason':'reference_reused_as_observation'}
        if any(v['label']==label for v in self.views):raise ValueError('Duplicate view label.')
        if len(self.views)>=self.max_views:raise ValueError('View budget exhausted.')
        raw={name:low_light_inspect(ref,image,self.matcher_config) for name,ref in self.references.items()}
        checked=review_results(raw,JointConfig(max_views=self.max_views))
        for names in self.aliases:
            for name in names:checked['parts'][name]['joint_status']='ambiguous_identity'
        for name,part in checked['parts'].items():
            if part['joint_status']=='reference_patch_supported':
                part['evidence_level']='geometric_patch_support';part['appearance']=None
            elif part['joint_status']=='ambiguous_identity':
                part['evidence_level']='ambiguous';part['appearance']=None
            else:
                part['appearance']=propose(self.references[name],image)
                part['evidence_level']='appearance_only' if part['appearance']['candidates'] else 'unresolved'
            part['physical_quantity']=None;part['independent_item_identity_established']=False
        item={'label':label,'image_sha256':digest,**checked}
        self.views.append(deepcopy(item))
        return {'accepted':True,**deepcopy(item)}

    def report(self)->dict[str,Any]:
        parts={}
        contested={n for names in self.aliases for n in names}
        for view in self.views:
            contested.update(n for conflict in view['conflicts'] for n in conflict['references'])
        for name in self.references:
            geometric=[v['label'] for v in self.views if v['parts'][name]['evidence_level']=='geometric_patch_support']
            candidates=[v['label'] for v in self.views if v['parts'][name]['evidence_level']=='appearance_only']
            level='ambiguous' if name in contested else 'geometric_patch_support' if geometric else 'appearance_only' if candidates else 'unresolved'
            parts[name]={'evidence_level':level,'supporting_views':geometric,'candidate_views':candidates,
                         'physical_quantity':None,'independent_item_identity_established':False}
        action='await_supplied_view' if not self.views else 'review_existing_crops'
        return {'schema':'countback-practical-development-0.3','opencv_version':cv.__version__,
                'parts':parts,'views':deepcopy(self.views),'distinct_views':len(self.views),
                'next_action':{'action':action,'camera_recapture_requested':False,
                               'instruction':'Review the evidence already available. Appearance-only locations are not verified identities.'},
                'runtime_gate':{'opencv5_executed':cv.__version__.startswith('5.'),'aws_executed':False,'competition_submission_ready':False},
                'images_uploaded':False,'kit_complete':None,'absence_verdict':None,'quantity_established':False,
                'development_only':True,'physical_kit_holdout':False,
                'scope':'One real user-supplied development set. Reference regions selected from closeups only. No view-coordinate labels enter inference. No physical counts or complete-kit certification.'}

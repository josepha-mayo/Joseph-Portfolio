"""Only source-anchored quotes can produce an answer or citation set."""
from __future__ import annotations
import json
import math
import re
import unicodedata
from .retrieval import identifiers

class GroundingError(ValueError): pass


def folded(s):
    return ' '.join(unicodedata.normalize('NFKC',s).split())


def contains_value(quote, value):
    q,v=folded(quote).casefold(),folded(value).casefold()
    if not v: return False
    # '94' must not be accepted solely because the passage contains '194'.
    return re.search(r'(?<!\w)'+re.escape(v)+r'(?!\w)',q) is not None


def parse_response(text):
    s=text.strip()
    if s.startswith('```'):
        s=re.sub(r'^```(?:json)?\s*','',s);s=re.sub(r'\s*```$','',s)
    data=json.loads(s)
    if not isinstance(data,dict):raise GroundingError('response is not an object')
    return data


def validate(data, context, *, query=None):
    """Grounding is checked; semantic necessity still requires a model evaluation."""
    answer=data.get('answer')
    evidence=data.get('evidence')
    if not isinstance(answer,str) or not isinstance(evidence,list):
        raise GroundingError('answer/evidence required')
    if len(answer)>512 or len(evidence)>8: raise GroundingError('response over budget')
    if not answer:
        if evidence:raise GroundingError('refusal must have no evidence')
        return {'answer':'','citations':[],'confidence':0.0}
    if not evidence:raise GroundingError('unsupported answer')
    available={x['cid']:x for x in context}
    selected={}
    finals=[]
    for e in evidence:
        if not isinstance(e,dict) or not isinstance(e.get('cid'),str) or not isinstance(e.get('quote'),str):
            raise GroundingError('invalid evidence record')
        cid=e['cid'];q=e['quote'].strip()
        if cid in selected:raise GroundingError('duplicate evidence chunk')
        if cid not in available:raise GroundingError('invented chunk')
        if not q or folded(q) not in folded(available[cid]['text']):raise GroundingError('invented quotation')
        role=e.get('role')
        if role not in {'bridge','value'}:raise GroundingError('invalid evidence role')
        selected[cid]={'chunk':available[cid],'quote':q}
        if role=='value':
            if not contains_value(q,answer):raise GroundingError('answer not in value quotation')
            finals.append(cid)
    if not finals:raise GroundingError('no value witness')
    # Every additional source must connect by an actual identifier in the quotes.
    reached={finals[0]}
    while True:
        extra=set()
        for cid,a in selected.items():
            if cid in reached:continue
            for other in reached:
                b=selected[other]
                if a['chunk']['source']==b['chunk']['source'] or identifiers(a['quote']) & identifiers(b['quote']):
                    extra.add(cid);break
        if not extra:break
        reached |= extra
    if reached!=set(selected):raise GroundingError('disconnected evidence')
    sources=sorted({s['chunk']['source'] for s in selected.values()})
    if query is not None:
        witnessed=' '.join(s['quote'] for s in selected.values())
        if not identifiers(query) <= identifiers(witnessed):
            raise GroundingError('query entity not witnessed by the evidence')
        if re.search(r'\bquarter\b',query,re.I) and re.fullmatch(r'Q[1-4]',answer,re.I) and re.search(r'Q[1-4]\s+FY\d+',witnessed,re.I):
            raise GroundingError('fiscal year qualifier dropped')
        if re.search(r'\brevision\b',query,re.I):
            complete=re.findall(r'REV[- ]?[A-Z0-9]+',witnessed,re.I)
            if complete and not any(re.sub(r'[- ]','',a).upper()==re.sub(r'[- ]','',answer).upper() for a in complete):
                raise GroundingError('revision prefix dropped')
    if any(s.startswith('/') or '..' in s.split('/') for s in sources):raise GroundingError('unsafe source path')
    # Numeric confidence is not scored. A schema-valid proof is not certainty.
    return {'answer':answer.strip(),'citations':sources,'confidence':0.5}

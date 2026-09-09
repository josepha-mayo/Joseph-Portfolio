function showRelated(){
 const s=snap(),c=selected(s),box=$('evResults');box.replaceChildren();
 if(!c||s.dirty){box.append(el('p','Select a current cut to search the rest of its transcript.'));return;}
 const stamp=signature(),query=$('evQuery').value;
 const rows=window.CutProofPassages.passages(s.cues,c,query);
 if(!rows.length){box.append(el('p','No related passage found by these lexical rules. This does not establish that all relevant context is included.'));return;}
 const current=()=>{
  if(signature()!==stamp||snap().dirty)throw new Error('These context results are stale. Find related passages again after changing the source or cut.');
  return snap();
 };
 for(const row of rows){
  const card=el('article',undefined,'ev-card');card.dataset.passageFirst=row.first;card.dataset.passageLast=row.last;
  card.append(el('strong',`${s.cues[row.anchor_index].id} / matching cue ${(row.distance_ms/1000).toFixed(0)}s outside cut`));
  for(const cue of row.cues){
   const quote=el('div',undefined,'ev-context-cue');quote.dataset.cueIndex=cue.index;
   quote.append(el('strong',`${cue.id} / ${CP.displayTime(cue.start_ms)} / ${cue.retrieval_match?'matched wording':'surrounding source'}`));
   quote.append(el('p',cue.text));card.append(quote);
  }
  card.append(el('p',row.reason,'ev-fine'));
  const play=el('button','Play source passage','small');
  play.onclick=safe(()=>{current();return playRange(row.start_ms/1000,row.end_ms/1000);});card.append(play);
  const limit=Math.min(120,s.result.options.maxSeconds),plan=window.CutProofPassages.repair(s.cues,c,row,limit);
  if(plan.allowed){
   card.append(el('p',`The repaired cut spans ${(plan.duration_ms/1000).toFixed(1)}s and adds ${plan.added_cue_ids.length} whole source cues, including intervening material.`, 'ev-fine'));
   const include=el('button','Include full intervening context','small');
   include.onclick=safe(()=>{
    const latest=current(),fresh=window.CutProofPassages.repair(latest.cues,selected(latest),row,Math.min(120,latest.result.options.maxSeconds));
    if(!fresh.allowed)throw new Error('This context no longer fits the current duration limit. Search again.');
    cancel();S.setRange(fresh.first,fresh.last);discard();fillEditor();showRelated();
    status('Expanded through the whole displayed passage, including its following cue. Every intervening word remains in order. Review is pending; exports use the new range.');
   });card.append(include);
  } else card.append(el('p',`Spanning this passage would take ${(plan.duration_ms/1000).toFixed(0)}s, over the ${limit}s limit. Inspect it instead of silently stitching separated claims.`,'ev-fine'));
  box.append(card);
 }
}

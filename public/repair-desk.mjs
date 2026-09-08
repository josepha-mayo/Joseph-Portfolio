/** Learner-owned line edits and a readable, tool-grounded study note. MIT. */
const linesOf = chain => String(chain).split(/\r?\n/).map(s => s.trim()).filter(Boolean);
export function reviseLine(chain, index, value) {
  const lines = linesOf(chain);
  if (!Number.isInteger(index) || index < 1 || index > lines.length)
    throw Error('Choose an existing step after the original problem, or append a step.');
  if (typeof value !== 'string' || !value.trim() || /[\r\n]/.test(value))
    throw Error('Write one equation on one line. Use the full workboard for several lines.');
  if (value.length > 300) throw Error('Keep this equation under 301 characters.');
  if (index === lines.length && lines.length >= 12) throw Error('This workboard supports at most twelve lines.');
  lines[index] = value.trim();
  const revision = lines.join('\n');
  if (revision.length > 4000) throw Error('The complete work is too long.');
  return revision;
}
export function nextMove(view) {
  if (!view) return {title:'Check your existing work',detail:'Paste your worked solution below. Relay checks every written transition, not just the final answer.',target:'begin'};
  if (view.audit.status === 'unsupported') return {title:'This step is outside the checker',detail:'Use the full workboard to revise the unsupported expression. It is not being graded as wrong.',target:'chain'};
  if (view.audit.status === 'changed') return {title:`Repair line ${view.audit.first + 1}`,detail:'Change that line only. Every later line stays in place and the full solution is checked again. A new error may become the next one to repair.',target:'stepValue'};
  if (view.phase === 'repair') return {title:'Your written steps agree so far',detail:'Append your next equation to isolate x. Equivalent unfinished work is not a completed solution.',target:'stepValue'};
  if (!view.card) return {title:'Now try fresh numbers',detail:'The repair checks out. A fresh-number task tests the operation without copying this worked answer.',target:'practice'};
  if (!view.card.answered) return {title:'Try the requested next step',detail:view.card.hints || view.card.revealed ? 'Help has been used on this card. A correct answer will stay assisted after saving or reopening.' : 'Your first answer has not used a hint or reveal. A revision will still be recorded as a revision.',target:'answer'};
  return {title:'Keep the evidence or try another',detail:'Export a readable study note, save the session, or request another fresh-number card. One correct attempt is not a mastery claim.',target:'studyNote'};
}
const code = value => '    ' + String(value).replace(/\r/g,'').split('\n').join('\n    ');
export function studyNote(report) {
  if (!report || !report.summary || !Array.isArray(report.attempts) || typeof report.current_chain !== 'string' || !/^[0-9a-f]{64}$/.test(report.source_digest || ''))
    throw Error('The server did not return a complete recomputed review.');
  const s = report.summary;
  for (const k of ['attempts','completed_cards','independent_first_attempts','assisted_completions','revised_completions'])
    if (!Number.isInteger(s[k]) || s[k] < 0) throw Error('Invalid recomputed review count.');
  const rows = ['# Counterstep Relay study note','','## The work I supplied','',code(report.current_chain),'','## Fresh-number practice',
    '',`Completed cards: ${s.completed_cards}. Independent first attempts: ${s.independent_first_attempts}. Assisted completions: ${s.assisted_completions}. Revised completions: ${s.revised_completions}.`,
    '', 'These categories come from replaying the supplied action history. They are not a school grade, authenticated authorship, or a measure of learning gain.'];
  if (!report.attempts.length) rows.push('', 'No fresh-number answers have been recorded yet. Completing the original repair does not count as independent transfer.');
  report.attempts.forEach((a,i) => {
    const outcome = ({requested_step:'Requested step checked',equivalent_other_step:'Equivalent, but a different operation',not_equivalent:'Changes the solution set',unsupported:'Outside the checker'})[a.outcome] || 'Review required';
    if(typeof a.question!=='string'||typeof a.instruction!=='string')throw Error('The review is missing the practice question.');
    rows.push('',`### Recorded attempt ${i+1}`, '', 'Requested operation:', '', code(a.instruction), '', 'Practice question:', '', code(a.question), '', 'My submitted equation:', '', code(a.answer), '', `${outcome}. Attempt ${a.attempt}. ${a.assisted ? 'Help was used.' : 'No hint or reveal was recorded.'} ${a.independent ? 'Independent first attempt recorded.' : 'Not counted as an independent first attempt.'}`);
  });
  rows.push('', '## Continue later', '', 'Open the saved handoff JSON in Relay to resume the same work and help history. This readable note is not an importable session.', '', 'Source session fingerprint:', '', code(report.source_digest), '', 'A fingerprint binds this note to supplied bytes, not to a person. Editing a session can create another valid personal-practice history.');
  return rows.join('\n') + '\n';
}
export function installRepairDesk({getCurrent,isBusy,isDirty,isReady,submitRevision,getReport,downloadText,onError}) {
  const box=document.createElement('section');box.className='repair-desk';box.id='repairDesk';
  box.innerHTML='<div class="next-move"><p class="eyebrow">YOUR NEXT USEFUL STEP</p><h3 id="nextTitle"></h3><p id="nextDetail"></p><button type="button" id="goNext" class="quiet">Go to this step</button></div><div id="lineRepair" hidden><h3>Fix one line. Keep the rest.</h3><p id="stepBasis"></p><ol id="stepList"></ol><label for="stepIndex">Step to change</label><select id="stepIndex"></select><label for="stepValue">Your replacement equation</label><input id="stepValue" maxlength="300" autocomplete="off" spellcheck="false"><button type="button" id="checkLine" class="primary">Check this line in the full solution</button><small>The original problem is locked. Relay does not fill in a correct answer for you.</small></div>';
  document.querySelector('.board .section-title').after(box);
  const note=document.createElement('button');note.type='button';note.id='studyNote';note.textContent='Readable study note';note.disabled=true;document.querySelector('.handoff-actions').append(note);
  const preview=document.createElement('section');preview.id='studyPreview';preview.className='panel study-preview';preview.hidden=true;preview.tabIndex=-1;preview.setAttribute('aria-label','Study note from the last checked session');
  const heading=document.createElement('h2');heading.textContent='Your study note';const pre=document.createElement('pre');pre.id='studyPreviewText';preview.append(heading,pre);document.querySelector('.handoff').after(preview);
  const $=id=>document.getElementById(id);let seen=null,noteDigest=null;
  function choose(){const current=getCurrent();if(!current)return;const index=Number($('stepIndex').value);$('stepValue').value=linesOf(current.view.chain)[index]||'';$('stepValue').focus()}
  $('stepIndex').onchange=choose;
  $('checkLine').onclick=async()=>{try {const current=getCurrent();if(!current || isBusy() || isDirty())return;const chain=reviseLine(current.view.chain,Number($('stepIndex').value),$('stepValue').value);await submitRevision(chain)}catch(e){onError(e)}};
  $('goNext').onclick=()=>{const target=nextMove(getCurrent()?.view).target;$(target)?.focus();$(target)?.scrollIntoView({block:'center',behavior:'smooth'})};
  note.onclick=async()=>{if(!getCurrent() || isBusy() || isDirty())return;try {const report=await getReport();if(report){const text=studyNote(report);noteDigest=report.source_digest;pre.textContent=text;preview.hidden=false;downloadText('counterstep-study-note.md',text);preview.focus({preventScroll:true});preview.scrollIntoView({block:'start',behavior:'smooth'})}}catch(e){onError(e)}};
  return {update(){const current=getCurrent(),view=current?.view,move=nextMove(view),disabled=!current||isBusy()||isDirty()||!isReady();$('nextTitle').textContent=isDirty()?'Check the edited work first':move.title;$('nextDetail').textContent=isDirty()?'The full workboard has edits that have not been checked. Check my repair before using line repair, practice, or exports.':move.detail;$('goNext').disabled=isBusy()||isDirty()||!isReady();note.disabled=disabled;if(!current||isDirty()||noteDigest!==current.capsule.sha256)preview.hidden=true;
    $('lineRepair').hidden=!view || view.phase==='practice';
    for(const id of ['stepIndex','stepValue','checkLine'])$(id).disabled=disabled;
    if(current && seen!==current.capsule.sha256){seen=current.capsule.sha256;const lines=linesOf(view.chain);$('stepList').replaceChildren();$('stepIndex').replaceChildren();lines.forEach((line,index)=>{const li=document.createElement('li');li.textContent=line;if(index===0){li.className='original';li.title='Original problem: locked'}else if(view.audit.status==='changed'&&index===view.audit.first){li.className='first-error';li.setAttribute('aria-label',`Line ${index+1}: first changed solution set. ${line}`)}$('stepList').append(li);if(index>0){const o=document.createElement('option');o.value=index;o.textContent=`Line ${index+1}`;$('stepIndex').append(o)}});if(lines.length<12){const o=document.createElement('option');o.value=lines.length;o.textContent=`Append line ${lines.length+1}`;$('stepIndex').append(o)}
      const index=view.audit.status==='changed'?view.audit.first:view.phase==='repair'&&lines.length<12?lines.length:Math.max(1,lines.length-1);$('stepIndex').value=String(index);$('stepValue').value=lines[index]||'';$('stepBasis').textContent='These are the last checked lines. Each edit is submitted through the real MCP repair tool.';
    }
    if(!current){seen=null;$('stepList').replaceChildren()}
  }};
}

/* CutProof passage context. Neighboring words are evidence to inspect, not a contradiction verdict. */
(function (root, factory) {
  const api = factory(typeof module === 'object' && module.exports ? require('./evidence.js') : root.CutProofEvidence);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CutProofPassages = api;
})(globalThis, function (E) {
  'use strict';
  const assert = (value, message) => { if (!value) throw new Error(message); };
  function validate(cues, clip) {
    assert(Array.isArray(cues) && cues.length > 0 && cues.length <= 3000, 'Expected 1 to 3000 source cues.');
    assert(clip && Number.isInteger(clip.first) && Number.isInteger(clip.last) && clip.first >= 0 && clip.last >= clip.first && clip.last < cues.length, 'Invalid selected range.');
    let previous = 0;
    for (const c of cues) {
      assert(c && typeof c.id === 'string' && typeof c.text === 'string' && c.text.length <= 10000, 'Invalid source cue.');
      assert(Number.isInteger(c.start_ms) && Number.isInteger(c.end_ms) && c.start_ms >= previous && c.end_ms > c.start_ms, 'Invalid source timing.');
      previous = c.end_ms;
    }
  }
  function passages(cues, clip, query = '', limit = 6) {
    validate(cues, clip);
    assert(typeof query === 'string' && query.length <= 300, 'Topic query exceeds 300 characters.');
    assert(Number.isInteger(limit) && limit >= 1 && limit <= 20, 'Invalid passage result limit.');
    // Keep the existing ranker unchanged; expand its hits into small source neighborhoods.
    const hits = E.related(cues, clip, query, 20);
    const groups = [];
    for (const hit of hits.slice().sort((a, b) => a.index - b.index)) {
      const before = hit.index < clip.first;
      const first = Math.max(before ? 0 : clip.last + 1, hit.index - 1);
      const last = Math.min(before ? clip.first - 1 : cues.length - 1, hit.index + 1);
      const previous = groups[groups.length - 1];
      if (previous && first <= previous.last) {
        previous.last = Math.max(previous.last, last);
        previous.hits.push(hit);
      } else groups.push({ first, last, hits: [hit] });
    }
    return groups.map(group => {
      const anchor = group.hits.slice().sort((a, b) => b.score - a.score || a.index - b.index)[0];
      const indices = new Set(group.hits.map(h => h.index));
      return {
        ...group, score: anchor.score, anchor_index: anchor.index, distance_ms: anchor.distance_ms,
        start_ms: cues[group.first].start_ms, end_ms: cues[group.last].end_ms,
        // Copy only source fields. Caller mutation must not alter the transcript or ranker hits.
        cues: cues.slice(group.first, group.last + 1).map((c, offset) => ({
          id: c.id, index: group.first + offset, start_ms: c.start_ms, end_ms: c.end_ms,
          text: c.text, retrieval_match: indices.has(group.first + offset)
        })),
        reason: 'Matched source wording with one neighboring cue on each side where available. Neighbors are context, not independently matched results. This is not semantic verification; more context may exist outside this passage.'
      };
    }).sort((a, b) => b.score - a.score || a.first - b.first).slice(0, limit);
  }
  function repair(cues, clip, passage, maxSeconds) {
    validate(cues, clip);
    assert(passage && Number.isInteger(passage.first) && Number.isInteger(passage.last) && passage.first >= 0 && passage.last >= passage.first && passage.last < cues.length, 'Invalid context passage.');
    assert(passage.last < clip.first || passage.first > clip.last, 'Passage must be outside the current cut.');
    assert(Number.isFinite(maxSeconds) && maxSeconds > 0 && maxSeconds <= 120, 'Context limit must be above zero and at most 120 seconds.');
    const first = Math.min(clip.first, passage.first), last = Math.max(clip.last, passage.last);
    const duration_ms = cues[last].end_ms - cues[first].start_ms;
    return {
      first, last, duration_ms, allowed: duration_ms <= maxSeconds * 1000,
      added_ms: duration_ms - (cues[clip.last].end_ms - cues[clip.first].start_ms),
      added_cue_ids: cues.slice(first, last + 1).filter((_, offset) => first + offset < clip.first || first + offset > clip.last).map(c => c.id),
      source_cue_ids: cues.slice(first, last + 1).map(c => c.id),
      interpretation: 'One continuous source interval, including every intervening cue and gap. Review must be renewed. No approval or truth judgment is implied.'
    };
  }
  return { passages, repair };
});

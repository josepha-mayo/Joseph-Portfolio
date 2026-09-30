# R52: conservative exact-citation minimization

Recorded 30 September 2026. Candidate stacked on R51; no grader image or submission is changed.

## Reproduced failure

The challenge grades citations as an exact set. R51 could accept a direct-answer proof containing a topically related but unnecessary extra source. Example: the correct bug-database row already contains ticket ORR-1847 and firmware 4.3.2, but an extra release-note source sharing ORR-1847 was also accepted, producing two citations where only one is necessary.

## Candidate

After ordinary strict validation succeeds, R52 may remove a bridge evidence item only when all of these are true:

- the question contains exactly one explicit identifier,
- the candidate item is a bridge, not the value witness,
- the bridge quote does not itself contain the answer,
- removing it still passes the complete strict validator, and
- removing it strictly shrinks the citation-source set.

This intentionally does **nothing** for zero-identifier questions, multi-identifier questions, answer-bearing alternate sources, or required graph bridges. In particular, the public no-ID multi-hop shape remains untouched.

## Evidence

Five new authored controls pass. Required two/three-file chains remain intact; no-ID multi-hop remains intact; answer-bearing alternate sources are not pruned. The full local suite passed **297/297**: all 292 R51 tests plus 5 R52 controls.

Local tested SHA-256:
- `von_rag/compact.py`: `019069cfed15c8ddc6edffc2722cfe2907b094e4ed49734898f092f1a3e11bd8`
- `tests/test_r52_citation_minimality.py`: `6b3f8db25d23c70cfd6122bd7df9f166f0167eb9c9ff5f1dc8fb897bcde8ee96`

## Promotion boundary

These are software/scripted-selection controls, not new model accuracy or a hidden score. Fresh AMD native inference and full-container qualification are still required before replacing MC3 R35.

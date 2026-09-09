# One-click Passage Repair

Click Load Passage Repair example in the Source panel. The original fictional recording is checked by hash before replacing the source. Existing work requires confirmation. Then open Evidence Desk, search related passages, inspect the source, expand through all intervening context, review and export. Loading grants no approval.

This add-on does not change the speech model, comparator, lexical ranker, Source Lock or renderer. The original v1.5, v1.4 and v1.3 releases remain independently pinned. Verification is in evidence/quickstart-release.json. Public-origin testing and competition metadata are separate.

For local use run python -m http.server 8765 --bind 127.0.0.1 from this extracted application folder, then open localhost:8765. Full-repository reproduction uses python upgrade16/release.py with Playwright, a real H264-capable Chromium, espeak-ng, ffmpeg and Node installed. The quickstart-reproduction directory retains the exact repository-oriented scripts, not a standalone installer.

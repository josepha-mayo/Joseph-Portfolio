# R56 native AMD promotion gate

Prepared 30 September 2026. This branch does not change the selected submission.

Candidate runtime commit: `b08d3f49c9ed663f3583bf0dcc9529230e26fb2e`.
Driver SHA-256: `450928ab2fd7076bb1079b8fc7bb6e119d4d09ce4e3d78debed8b98f8cfb018b`.
Official starter-kit SHA-256: `1173aef83fa06828b1acba231bc033f52658d4f9714d6a61a17873e4607f0829`.

The driver compares selected R35 against exact R55 using the existing pinned Qwen3-VL-4B checkpoint and production reader on a real AMD GPU. CPU fallback is forbidden and model/network downloads are disabled during evaluation.

Each variant runs:
- 10 official public-sample questions;
- 12 existing authored stress questions;
- 25 deterministic predeclared new questions.

The 25 new cases include repeated-scope quarters, genuine current conflicts, voltage-conditioned values, min/max property separation, unit-price tiers, mixed current/withdrawn records, one stale-Python-comment case, and citation distractors. Labels remain outside indexed corpora.

The six R55 runtime overlays are fetched from the immutable candidate commit and SHA-256 checked before use. R35 source bytes and the production reader are also hash-pinned before any GPU evaluation. Results record exact answer + exact citation-set correctness, completed responses, per-query time, GPU calls and peak PyTorch memory.

No R56 GPU run has occurred yet. At the latest check, the old notebook backend returned 502 and the dedicated AMD dashboard was signed out. No quota bypass, credential extraction, duplicate allocation or paid resource was attempted.

Promotion requires: no R35->R55 regressions on the paired run, then a separate official full-container AMD self-check. Software CI or native source-path success alone must not replace MC3 R35.

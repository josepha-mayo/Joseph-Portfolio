# CutProof 1.2 / Evidence Desk

This is an additive candidate; v1.1 remains at its immutable submitted URL until verification passes.

## New workflows
- Video-first captions: optional quantized Whisper-tiny.en runs inside a Web Worker using Transformers.js 3.8.1 and ONNX Runtime Web. Explicit download consent. No inference API or audio upload.
- Speech/caption disagreement: align independently recognized speech with supplied captions. Negation, quantity and qualifier differences are highlighted, not declared proven errors. Export includes the actual source SHA-256, transcript SHA-256, range and pinned model revision.
- Source-wide context retrieval: BM25 lexical relevance plus framing-word cues can surface distant related passages. Exact source playback; contiguous expansion only when it fits the time limit.
- Explicit caption correction: preserves source timing, updates the transcript and clears all approvals. Generated captions require explicit application.

## Honest bounds
English speech model. 10-minute / 120 MB decode limit. ASR timestamps are estimates; noisy audio, accents, music and silence can cause mistakes. Whole-source retrieval is lexical, not semantic contradiction detection. Normalization covers common contractions and numbers 0-99, not every spoken numeric expression. A match with ASR does not prove accuracy. Existing boundary-rule diagnostic results are not upgraded by these new workflows.

Serve this directory with HTTP or HTTPS. The original core editor remains available separately as the v1.1 offline standalone. Optional speech downloads public model files on demand and caches them when the browser permits it. No claim is made that a first-time speech run works offline.

## Attribution
Original project code: MIT (parent LICENSE). Transformers.js: Apache-2.0; ONNX Runtime: MIT (vendor licenses). Whisper-tiny.en: MIT; ONNX conversion from onnx-community/whisper-tiny.en on Hugging Face. Neural narration uses hexgrad/Kokoro-82M and stock af_heart voice, Apache-2.0. No individual's voice was cloned. Narration and missing-word test material are synthetic. The natural-speech smoke fixture comes from OpenAI Whisper tests/jfk.flac, a historical public speech; it is not an independent benchmark.

## Reproduce
Serve the extracted directory with python3 -m http.server 8000 and open http://localhost:8000. The provided index.html is already built. The v1.1 base source and the explicit upgrade recipe are included; the complete build workspace is also available in the linked GitHub project directory. CI installs CPU-only dependencies, synthesizes the original fixture, exercises real browser ASR without passing reference captions to the model, and preserves logs even on failure. Failed runs are not relabeled successful.

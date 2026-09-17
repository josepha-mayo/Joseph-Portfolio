CUTPROOF EDIT BUNDLE

Captions are relative to each clip. The manifest retains absolute source times.
Video is not embedded. Use the original video that matches the transcript.

Native render, with Python 3.10+ and FFmpeg/ffprobe installed:
  python render.py --bundle . --media "your-source.mp4" --out rendered

The renderer validates transcript provenance and source duration before encoding.
A matching transcript fingerprint is not proof that the transcript matches the audio.
No video has been uploaded or published by exporting this bundle.

SOURCE LOCK (v1.3)
manifest.json binds this handoff to the SHA-256 and byte size of the attached media. The bundled native renderer rejects different bytes before creating outputs. Re-encoding changes the hash. A digest is editable, not a signature or source-authenticity proof. The transcript is still supplied or model-estimated and must be reviewed.

Portable project restore remains a cue/range handoff with reviews reset; it does not automatically authenticate the reattached file. Use Source Lock with manifest.json to compare the file explicitly.

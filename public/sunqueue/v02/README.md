# SunQueue Replay 0.2

A planning and fixed-schedule replay workbench. The core model remains v0.1: one machine, at most four jobs and 24 hourly slots. Replay does not optimize the frozen starts against the new profile. The current demo and profiles are synthetic; no field calibration, customer trial, revenue or award is claimed.

Run the standalone index.html in a browser. No external runtime downloads or account required. Original code is MIT. Stock synthetic narration uses Kokoro-82M / af_heart, Apache-2.0, without cloning anyone.

Source archive includes the original source, tests and upgrade02 extension. Run `python build.py`, `python upgrade02/build.py`, `node --test tests/core.test.cjs upgrade02/replay.test.cjs`, `python tests/oracle.py`, and `python upgrade02/browser.py`. Browser tests require Playwright and Chromium. Full video reproduction is `python upgrade02/release.py` with Kokoro 0.9.4, torch 2.8.0 CPU, soundfile 0.13.1, Playwright 1.55.0, ffmpeg and espeak-ng installed.

A second entry is being prepared for Next Founders. This is the same SunQueue project previously entered into NextStep, not a claim of two separately invented products. Both build revisions were created September 7, 2026 with substantial AI assistance.

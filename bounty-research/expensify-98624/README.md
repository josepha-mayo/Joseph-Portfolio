# Expensify #98624: source-level scope diagnostic

This is an AI-assisted investigation on Joseph Ayanda's behalf, not an upstream fix or claim of a bounty. No Expensify code has been modified and no upstream PR has been opened. Portfolio production is unchanged.

## Scope

The diagnostic evaluates the source-side file-replay and attachment-cache behavior discussed in [Expensify/App#98624](https://github.com/Expensify/App/issues/98624), separately from the existing image-flicker work. The underlying re-rooting diagnosis and basic fix were already proposed by [Abdulloh0109](https://github.com/Expensify/App/issues/98624#issuecomment-5414060689) and discussed by [MelvinBot](https://github.com/Expensify/App/issues/98624#issuecomment-5532696271). This report does not claim those ideas as a new discovery or a duplicate proposal. Its addition is an executable, pinned-source diagnostic and narrower statements about what the checks do and do not establish.

Pinned App source: `9f9ddbd4b4edfc615a9cec78aa24da45188f9f1a`.

Compared PR #85588 head: `NJ-2020/Expensify@8bd936dd3e4e705509e7c94809a666330732e171`. Its native prepareRequestPayload file is byte-identical to the pinned main file, Git blob `080249e8d0618c57458eaa05a464565ca7ab3314`. The PR was still an open draft when inspected. Its storage/caching changes are not treated as a merged fix.

## What executes

`diagnose.cjs` transpiles the unchanged TypeScript modules, including the real ReceiptStorage resolver, FileUtils.readFileAsync, native prepareRequestPayload, native attachment actions and the web payload implementation. It does not duplicate their function bodies or inject a ready-made solver response.

Two synthetic container roots are created in a temporary directory. Only the CURRENT root contains the PNG fixture. Local fetch and RNFS boundaries map to actual Node readFile, copyFile and filesystem-existence operations. The missing STALE path therefore raises a real filesystem error. Native FormData, Onyx, platform APIs, file-type classification and telemetry are controlled adapters/spies. The platform value is set to iOS for JavaScript control flow, not because an iOS device is running.

The script has 15 checks and passed locally on Node 22.16.0 / TypeScript 5.8.3. The separate GitHub Actions diagnostic fetches the six exact source files and verifies their SHA-256 hashes before running the same script.

Key observations:

- Offline `file` input with a stale receipts path returns FormData containing the comment but no file. No API request is sent by this diagnostic; it does not claim the backend accepted that comment.
- Resolving the INPUT first supplies the exact bytes successfully to the unchanged function. This is a diagnostic control, not a tested patch.
- The `receipt` branch already resolves the same stale path.
- A genuinely missing file is also omitted. Re-rooting alone cannot fix absence, so error/telemetry policy needs separate agreement.
- There IS a FileUtils console.debug on read failure. The gap is missing dedicated upload-failure telemetry, not literally zero logging.
- The native cache copy from a stale receipts URI fails with ENOENT and writes no Onyx cache record. Resolving the input first copies the exact bytes and writes the record.
- The current ReceiptStorage resolver does NOT re-root Library/Caches/attachments paths. Resolving every cache path through it is not, by itself, a general cache-location repair.

## Reproduce

Use the checked-in `.github/workflows/expensify-scope-diagnostic.yml`. It lists the source URLs, hashes, exact Node and transpiler versions, and command. To run locally, retrieve the six source files into a `snapshot/` tree preserving their repository paths, install TypeScript 5.8.3 outside the application, then run:

```sh
NODE_PATH=/path/to/typescript-install/node_modules node diagnose.cjs ./snapshot ./evidence
```

The harness exits nonzero on a failed check and writes `evidence/diagnostic.json`. No customer credentials are required and the tests make no network or API calls after the public source is downloaded.

## Not established

No native app upgrade, iOS or Android device/emulator test, UI rendering, production failure rate, end-to-end queued upload, codebase-wide typecheck/lint or proposed fix validation is claimed. Source-level control-flow checks do not replace required native QA. Maintainer scope acceptance, assignment, verified contributor onboarding, Upwork hiring and payment are all still pending.

Do not merge this research branch into the unrelated portfolio production branch. Do not open an Expensify PR before the contributor workflow's acceptance and hiring steps.

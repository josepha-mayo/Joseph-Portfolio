# Countback: Inspect the Evidence

Technical report working draft, 11 September 2026.

**Status: not a final submission.** Native software and local Lambda-container execution are verified. Actual AWS execution, independent photographic evaluation, the final architecture diagram, judge demonstration arrangements and video remain incomplete. This document does not claim organizer eligibility approval.

## 1. Problem and intended users

A repair desk or equipment-loan desk needs to review returned items against reference photographs without treating a plausible visual resemblance as proof of a complete kit. Countback presents what the supplied photographs support, requests another supplied view when evidence is unresolved, and separates automated evidence from an operator's judgment.

The intended benefit is an inspectable review and handoff. Reduced review time, identification accuracy, adoption and financial benefit have not been established by a user study.

## 2. Implemented workflow and architecture

1. The local Photo Workbench accepts reference photographs with explicitly chosen crops and ordered group views. The operator must authorize local processing.
2. The bounded local HTTP server validates the request and invokes a real OpenCV 5 worker. It does not return a prewritten match report.
3. The deterministic evidence controller inspects a supplied view and uses its result to decide whether another supplied photograph needs inspection. It does not inspect future-image contents before deciding to inspect that view.
4. Automated results distinguish geometric patch support, weaker appearance/internal-pattern evidence and unresolved cases. Matching evidence is not a quantity, condition or unique-instance certificate.
5. The Review Desk exposes the evidence and collects explicit operator assessments and reasons. History, saved sessions and downloaded handoffs preserve the distinction between algorithmic output and human assessment.

The current cloud adapter accepts a bounded inline event and validates image hashes, formats, dimensions, oriented crops, reference names and duplicate views. The packaged adapter was exercised through AWS's local Runtime Interface Emulator (RIE) on GitHub-hosted compute. That is a separate path from a deployed AWS Lambda function.

The final diagram must show implemented local components separately from any subsequently verified AWS components. This narrative is not a claim that the required final diagram has been delivered.

## 3. OpenCV 5 and source identity

The preceding native-browser verification used OpenCV 5.0.0 and the image-contract source revision:

- Source: `2a31cc800821eb5e743010f50ea0e1306185dc58`
- Native run: https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/34532678408

The container was tested at:

- Source: `5fa575065511d58f5d84694a2ff265232f9b0450`
- Container run: https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/34538542333
- Public source: https://github.com/josepha-mayo/Joseph-Portfolio/tree/5fa575065511d58f5d84694a2ff265232f9b0450/countback-workbench
- Recorded container audit: https://github.com/josepha-mayo/Joseph-Portfolio/blob/f6e5db9a2da4684f49f3871cad5719e270f7214f/countback-verification/lambda-container-20260910.json

The container runtime was Python 3.13.15, OpenCV 5.0.0 from `opencv-python-headless==5.0.0.93`, NumPy 2.3.5 and Pillow 12.3.0, on Linux amd64. The headless distribution is not claimed to be byte-identical to the desktop distribution. The packaging change left all 29 inherited manifested source/test files unchanged.

No COOL or Graviton execution is claimed. The current x86 container is not evidence for the Best Use of COOL award.

## 4. Executed verification and its limits

| Evidence | Observed result | What it establishes |
|---|---|---|
| Native image-contract run | 72 Python tests, 31 JavaScript tests and 14 native browser checks passed | Real browser-to-HTTP-to-OpenCV execution and review/download behavior on generated fixtures |
| Lambda container runtime | The same 72 Python tests passed | Retained behavior in the packaged native runtime, not 72 additional independent tests |
| RIE HTTP execution | Nine checks across eight invocations passed | Cold/warm analysis, invalid-input refusal, subsequent valid recovery, provenance and temporary-file cleanup |
| Runtime containment | Non-root UID 10001, read-only root, no external network or published ports, 2 GiB RAM, two CPUs, 512 MiB temporary filesystem, 90-second function setting | Properties of the tested local container configuration, not AWS IAM or production-security certification |
| September 11 artifact audit | Downloaded ZIP and inner image TAR match recorded SHA-256 values | Byte identity of the retained image copy, not a fresh execution of that image |

Rejected RIE cases covered missing permission, changed image bytes, repeated group photographs, invalid crops and reserved reference labels. A valid request succeeded after those refusals. These software controls are not held-out recognition-accuracy measurements.

The prior local browser-policy failure remains a failed attempt. Subsequent successful native runs are independent records of execution, not a reinterpretation of that failure. Tests repeated in different environments are not summed as new unique coverage.

## 5. Photographic observations

Five author-supplied photographs were used during development: three references and two group views. The booklet retained geometric patch support; the remote retained internal-pattern consistency in the second view; the luminous mouse remained appearance-only. These are reused development cases. They do not establish representative accuracy, quantity estimation or unique-instance identity.

The original photographs and derived private reviews are excluded from public source and were not used in the container fixture checks. No human assessment is fabricated. Automated test assessments remain labeled as tests.

## 6. Independent evaluation plan, not completed results

Freeze the tested engine revision before selecting evaluation cases. Select legally usable independent photographic cases and retain a provenance/license record. Do not request retakes of the five already supplied development photos merely to repeat the same stage.

The evaluation should separate development from test objects/scenes and include lookalikes, absent items, occlusion, repeated designs, changed arrangements and low-texture objects. Human reference judgments must be distinguishable from generated software-test labels. Choose metrics that match the actual claim: supported correspondence, unsupported-match errors, unresolved/referred cases and whether an additional view changes the decision. Do not infer complete-kit accuracy from patch correspondence.

Compare first-view-only review with the existing adaptive supplied-view workflow on the same frozen cases. Record failures and latency measurements with their hardware and input provenance. A synthetic stress suite may test implementation behavior but must not be labeled an independent photographic benchmark. Operator task time and usefulness require a separate authorized user evaluation.

No case count, recognition score, latency improvement or human-study result is entered here because that evaluation has not yet been executed.

## 7. AWS deployment: explicitly incomplete

No registry push, AWS Lambda function or public application endpoint has been deployed in this workstream. The available connection was last observed using account-root identity; that is not the deployment identity to use. A permitted non-root identity, selected region, explicit spending ceiling and data-transfer scope are still required. Organizer late-entry eligibility is also unresolved.

After those prerequisites are resolved, the proposed minimum step is a bounded deployment of the tested image and authenticated invocation with generated fixtures. Record the actual function version, image identity, AWS request identity, observed response, cleanup behavior and available cost evidence. Then integrate the approved AWS path into the demonstration. An environment variable or local RIE response is not proof of AWS execution.

The final requirements allow a working web endpoint **or an arranged live screen-share demonstration**. A public upload endpoint is therefore not automatically required. The screen-share alternative must actually be arranged; it is not currently confirmed.

## 8. Responsible use and operating boundaries

Local processing permission is not permission for cloud transfer or public publication. Private development photos stay private unless separate authorization is supplied. The local server is loopback-only, admits one analysis at a time, validates origin and a per-process token, bounds worker execution, removes temporary uploads and expires a bounded set of in-memory reviews. Downloaded outputs remain under the operator's control.

Image hashes establish byte correspondence, not consent, authenticity or truth. Partial occlusion and weak texture can leave cases unresolved. Evidence views can mislead if treated as definitive identity or completeness checks. Do not use this prototype as an automatic acceptance decision for safety-critical equipment. Human review remains explicit.

## 9. Submission completion checklist

- [x] Substantive real OpenCV 5 local execution recorded.
- [x] Native browser workflow recorded.
- [x] Tested Lambda-compatible image and reproducible build/test sources recorded.
- [x] Downloaded exact tested image and independently checked both archive hashes on September 11.
- [x] First technical-report draft written.
- [ ] Obtain organizer decision on late-proposal eligibility and the controlling deadline.
- [ ] Resolve non-root cloud access, spending ceiling and data-transfer scope.
- [ ] Execute and document a meaningful component on AWS.
- [ ] Complete independent photographic evaluation and report failure cases.
- [ ] Produce a final architecture diagram distinguishing actual local and AWS paths.
- [ ] Provide a working endpoint or arrange the allowed live screen-share route.
- [ ] Record a judge-accessible video no longer than five minutes showing the team, application, architecture and principal results.
- [ ] Package required code/archive, pinned dependencies and testing instructions.
- [ ] Finalize this report against observed results, complete required form fields, submit the existing draft and read back Submitted status.

The current submission fields include Repository URL (28209) and Testing instructions (28210). Working web endpoint (28211) is optional. The native requirements response also marks a ZIP and video required. Special Award Consideration (28208) is optional and must be justified by executed evidence; no special-award qualification is asserted here.

## 10. Image preservation record

Source artifact 10176371365 originally expires at `2026-09-17T22:40:24Z`. Its downloaded conversation copy is named `Countback-Tested-Lambda-Image-20260911.zip`.

- ZIP size: 291,687,949 bytes.
- ZIP SHA-256: `a298a354afeef4dfc3108602f056d9f3b1a53501c0925f58f15350d785ff7ed6`.
- Sole ZIP member: `countback-lambda.tar`, 810,479,616 bytes.
- Inner TAR SHA-256: `5600736960ba040892b756cd76d74c81db529ed7373f53fdde6448bdf77b76e0`.

Both hashes were freshly calculated and matched on September 11. The image was not rerun in the chat container. This download does not extend GitHub's expiry or guarantee permanent chat storage; retain the provided archive as a personal backup. No private photos, cloud credentials or account identifiers are included in this report.

## Primary references

- Official event and final requirements: https://opencv26.devpost.com/
- Formal rules: https://opencv26.devpost.com/rules
- Existing project: https://devpost.com/software/countback-inspect-the-evidence
- Native run and tested source links in section 3.
- Container reproduction instructions: https://github.com/josepha-mayo/Joseph-Portfolio/blob/5fa575065511d58f5d84694a2ff265232f9b0450/countback-workbench/cloud/CONTAINER.md

The event overview and submission fields were freshly read on September 11, 2026. This is AI-assisted documentation of recorded work, not proof that the remaining requirements are complete.

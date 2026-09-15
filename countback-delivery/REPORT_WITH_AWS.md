# Countback
## Inspect the evidence before signing off a returned kit

**Technical report | 15 September 2026**  
**Joseph Ayanda | Solo builder, Nigeria**  
OpenCV AI Competition 2026, powered by AWS

### A review aid, not an automatic acceptance decision

A repair desk or equipment-loan desk must decide whether photographs provide enough evidence to check returned items. Clutter, changed viewpoints and partly hidden objects make a plausible resemblance easy to overstate. Countback compares enrolled reference photographs with supplied scene views, exposes the evidence, and keeps an operator's assessment separate from the algorithm's result.

The implemented product is a local Photo Workbench. It accepts reference crops and up to three ordered scene views, requires processing permission, executes OpenCV 5, and produces a review that can be saved and exported. When a first image leaves an item unresolved, a bounded controller inspects the next supplied photograph. It does not control a camera or inspect future images to select the most favorable result.

The optional viewpoint-aware review mode uses foreground filtering, affine-view synthesis and distinct SIFT landmarks. It can focus attention on a plausible corresponding patch. When that evidence is unavailable, it presents the original scene without a weak colour-only highlight. No automatic identity, quantity, condition or complete-kit verdict is produced.

### Delivered evidence

A corrected, extracted-ZIP-tested application; a fresh-view photographic diagnostic; actual image analysis on AWS Lambda; recorded failure and recovery cases; a narrated application demonstration; and reproducible source and input fingerprints. The private AWS trial is complete and its resources have been removed.

**Submission state:** technical and media materials prepared. A public video must be attached to the existing entry, and the required judge endpoint or live screen-share arrangement must be completed. No organizer eligibility approval or final submission is claimed by this report.

<div class="pagebreak"></div>

# 1. Architecture and data flow

![Implemented local workflow and completed AWS trial](Countback-Architecture.svg)

**Local path.** The browser sends authorized images to a loopback HTTP service. The service checks formats, dimensions, hashes, crops and view duplication, admits one job, and runs a subprocess with a 90-second limit. The original controller produces evidence tiers and a trace. The optional affine refinement uses only views the controller actually inspected. The reviewer sees tentative focuses or full photographs and records a judgment and reason; raw machine evidence remains intact.

**AWS path, executed separately.** A temporary, branch-restricted GitHub OIDC role deployed a private digest-pinned image to Lambda in `us-east-1`. An authenticated client sent bounded inline requests to published version 1. This ran the original OpenCV analysis handler, not the local affine refinement. The actual AWS API responses, request identifiers, function configuration, image digest and logs are preserved. There is no automatic local-to-cloud transfer.

The diagram distinguishes two implemented execution paths. It does not claim that the local user interface remotely invokes Lambda. Neither an AWS SDK import nor the local Runtime Interface Emulator is used as proof of cloud execution.

<div class="pagebreak"></div>

# 2. Photographic evaluation

### Protocol before prediction

The fresh cohort contains **18 RGB photographs from nine preselected clips in two environments**, with the same nine previously enrolled reference objects. Reference crops, clip identities and one-third/two-thirds frame-selection rules were fixed before inference. It forms 18 paired cases and 54 target queries: 24 visible targets and 30 targets absent from the supplied photographs. Observation masks and pose records were reserved for separate scoring, not supplied to the matcher.

Data: **UW Indoor Scenes (UW-IS) Occluded Dataset v1**, Figshare article 20506506, CC BY 4.0. Authors: Ekta U. Samani, Xingjian Yang, Srivatsa Grama Satyanarayana and Ashis G. Banerjee. No endorsement is implied.

| Review-region method | IoU >= 0.30 / 24 | IoU >= 0.50 / 24 | Regions on 30 absent queries |
|---|---:|---:|---:|
| Original first view | 7 | 6 | 18 |
| Original adaptive views | 9 | 8 | 23 |
| Conservative foreground | 9 | 7 | 23 |
| Affine overlay | 11 | 9 | 23 |
| Affine-only focus | 5 | 4 | 0 |

Bounding-box overlap is a **localization screen, not identity accuracy**. The affine overlay improved localization but retained many inherited weak guesses. The optional display policy therefore uses eligible landmark focuses and otherwise opens the full photograph. That policy was selected after inspecting these results; its functional tests are not an independent confirmation of user benefit.

### What did not work

Overall coverage remains limited, particularly for low-texture objects. All original machine-supported query counts stayed at zero. Shared physical objects, related frames and only two environments prevent a representative generalization claim. Zero absent-query highlights in the small affine-only sample is not a zero-false-positive guarantee. The next research question is whether better descriptors increase useful focus coverage without recreating the weak-proposal burden.

<div class="pagebreak"></div>

# 3. Actual AWS execution

**Completed 15 September 2026, 21:07:33-21:08:54 UTC.** GitHub run 35023729856 used a dedicated assumed role, not root, for deployment and invocation. The private function ran the previously tested original image, on x86_64, with **2 GiB memory, 90-second timeout and 512 MiB temporary storage**. No public URL, trigger, provisioned capacity or GPU was created.

| Invocation | Observed outcome | Client wall time |
|---|---|---:|
| Generated cold request | Valid geometric evidence | 10.007 s |
| Generated warm request | Valid geometric evidence | 0.685 s |
| Permission not granted | Expected rejection | 0.152 s |
| Bytes differ from hash | Expected rejection | 0.064 s |
| Repeated group view | Expected rejection | 0.094 s |
| Reference crop out of bounds | Expected rejection | 0.094 s |
| Reserved reference label | Expected rejection | 0.063 s |
| Valid request after refusals | Recovery passed | 0.520 s |
| Public-photo request | Two views analyzed; three references appearance-only | 5.265 s |

**Nine checks passed: four valid analyses and five expected refusals.** They are not nine recognition successes. The public-photo engine portion took **4.957 seconds** and did not establish identity. It reused an already evaluated scene, so it adds hosting/transport evidence, not another accuracy trial. Only generated fixtures and licensed public images were transferred.

Every request has an input fingerprint and an AWS response receipt. Returned provenance was checked against the exact uploaded image hashes. The unchanged handler's internal environment-level AWS verification flag stays false; the external AWS API, published version and resolved image establish the actual hosting evidence.

<div class="pagebreak"></div>

# 4. Containment, cleanup and cost

### Limited privileges and lifetime

The deployment role trusted only the exact Countback release branch of `josepha-mayo/Joseph-Portfolio`, with the required audience and a time-limited policy. It could affect only the dedicated trial registry, function and logs and pass only the separate Lambda runtime role. The runtime role could write only its log streams. No stored access keys or administrator policy were created.

The account's regional concurrency quota was ten. The trial did not request a reserved-concurrency allocation. Requests were issued sequentially by the client; this is not a service-enforced single-concurrency guarantee. The client disabled automatic invocation retries and made nine calls within the approved maximum of twenty.

### Cleanup verified independently

The runner deleted its function, registry and log group after capturing results. A separate AWS API check at **21:10:28 UTC** confirmed they were absent, checked ownership and exact policies, and removed the two trial-created roles and OIDC provider. Final reads found no trial roles or GitHub provider. Unrelated resources were left intact. No standing judge endpoint remains.

### Cost evidence, not an invoice

AWS logs record **15.434 billed seconds at 2 GiB**, or **30.868 GB-seconds**. At the published first-tier x86 Lambda rate of $0.0000166667 per GB-second and $0.20 per million requests, the compute-plus-request estimate is **about $0.00052 before credits and tax**.

This estimate excludes ECR and log charges and is not the finalized account bill. It must not be presented as the total AWS spend. The approved $5 ceiling was an operating budget, not a provider-enforced billing cap. Resource creation and removal timestamps, allocation and billed-duration logs are included for inspection.

Pricing reference: https://aws.amazon.com/lambda/pricing/

<div class="pagebreak"></div>

# 5. Software verification and reproduction

### Test the delivered bytes

Delivery run **35001804236** exercised the extracted application ZIP, not just its repository checkout: **85 Python tests, 31 JavaScript tests, seven packaging guards, 14 original-mode browser checks, the same 14 checks in optional pose mode, and eight public-photo integration checks** passed. Repeated assertions across modes are not additional independent coverage.

A previous packager omitted `engine/evidence_workflow.py` because its name started with `evidence`. The current package requires that module, checks its hash, and runs imports and the browser/server/engine path after extraction. Anonymous downloads of the published ZIP and checksum files were verified. The local application ZIP is unchanged by the AWS trial or this report.

### Run the local application

Extract the whole `Countback-Local-Candidate.zip`. Use Python 3.13; inside `countback-workbench`:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-workbench.txt
python pose_workbench.py
```

On Windows, activate `.venv\Scripts\Activate.ps1` instead. Open the printed loopback address. Choose reference crops, supply group views, allow processing, inspect the result, enter an assessment and export. `python workbench.py` starts the original mode. Node.js 22 and Playwright 1.57.0 are used by the documented test suite. Pinned application requirements remain inside the package.

### Reproduce the cloud experiment

`countback-delivery/aws_trial.py` and its workflow preserve the input construction, image checks and expected refusal cases. Reproduction requires a newly authorized non-root identity, the private image and explicit budget. The temporary credentials and trial resources have been deleted. Re-running is not necessary to inspect the archived receipts. The complete repository retains the historical image build and deployment sources.

<div class="pagebreak"></div>

# 6. Responsible use and judge delivery

### What the product does not establish

A matching patch is not proof of a unique physical item, condition, quantity or kit completeness. A missing visible match may reflect occlusion, texture or an unhelpful viewpoint. Do not use this prototype to automatically approve safety-critical equipment. The operator can inspect the original photograph and record uncertainty instead of accepting a highlighted region.

Human assessments start pending. The demonstration contains one clearly labelled scripted review note to exercise the export path; it is not an independent customer assessment. Exported files are inspectable records, not tamper-proof certificates or authenticated grades.

### Privacy and operational boundaries

The development service remains loopback-only. It validates origin and a process token, enforces one active job and a subprocess deadline, deletes temporary uploads and expires bounded in-memory reviews. Downloaded files remain with the operator. Specific existing display masks are not a general private-information detector. Byte hashes show consistency, not authenticity, permission or truth.

No private author photographs were used in the AWS trial or included in public delivery. Permission for local processing is not permission for cloud transfer. The narrated presentation uses one stock neural voice, not a voice clone or a human-recording claim. Original source is MIT licensed, developed by Joseph Ayanda with AI assistance; dataset rights remain separate.

### Remaining administrative gates

The competition accepts a working endpoint or an arranged live screen-share. This package supplies a reproducible local app and recorded evidence, but does not itself establish a booked live session. The earlier question about entry without an August proposal also has no organizer-specific confirmation in the reviewed correspondence. Final entry status must be read back from Devpost after required uploads and arrangements, not inferred from a published project page.

<div class="pagebreak"></div>

# 7. Evidence index

### Application and evaluation

- Tested local source: `2d6f2537de83f7ea2da405d95961fc405d39b890`.
- Local release: https://github.com/josepha-mayo/Joseph-Portfolio/releases/tag/countback-local-v0.5-rc1
- Extracted-package verification: https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/35001804236
- Frozen original engine: `d6f8be84da041b3a41ba19d3cb29c1c5c85f0e9d`.
- Fresh protocol and results: `countback-validation/FRESH_EXECUTION_PROTOCOL.json` and `FRESH_RESULTS.json` at `b1e3b779710e79b3f65490524cb5fe3b93676fc6`.
- Dataset: https://figshare.com/articles/dataset/UW_Indoor_Scenes_UW-IS_Occluded_Dataset/20506506

### AWS trial and image identity

- Trial source: `7965afe4a87773b9853d2e2dda08491c36fb7b87`.
- Actual execution: https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/35023729856
- Artifact 10417844415; archive SHA-256:
  `75b0e3a3d2fecef75e2ee4bdfd64c8749ee6c5c0f0486008dede9752340b1ad8`.
- Private ECR image digest:
  `sha256:3e99eb3e351a333fcf6f632226fa2120de0e1450c25fe458267bb7297d30e238`.
- Published Lambda version: **1**, `us-east-1`.
- Trial files: `AWS_TRIAL.json`, `FUNCTION_PROVENANCE.json`, `PUBLIC_INPUTS.json`, nine response files and separate `AWS_CLEANUP.json`.

The evidence distinguishes successful analyses, expected refusal cases, historical local tests, public-photo limitations and deletion receipts. Account identifiers are redacted in the public trial records. No credentials or private photos are bundled.

### Official specifications

- Competition and submission requirements: https://opencv26.devpost.com/
- Existing project: https://devpost.com/software/countback-inspect-the-evidence
- AWS Lambda container images: https://docs.aws.amazon.com/lambda/latest/dg/images-create.html
- AWS pricing: https://aws.amazon.com/lambda/pricing/

**Report scope:** a documented prototype and completed private cloud experiment. No prize, revenue, customer adoption, broad security certification, representative recognition accuracy or final competition submission is asserted.

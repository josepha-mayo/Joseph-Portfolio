# GeoDrift

**A database update can change who your application lets through. Rehearse it before rollout.**

GeoDrift is a complete offline IP2Location CSV comparison application and streaming Python library/CLI. It compares two country snapshots, applies the operator's before/after country policies, and reports exact affected IP intervals, coverage changes and optional aggregate request replay. It does not sample individual addresses or turn a missing classification into permission.

**No account, API key, network probe, external inference or firewall modification.** The browser runs the actual engine in a Web Worker. The Python CLI reads large country snapshots as streams. Country labels are supplied classifications, not verified residence, nationality or identity.

## Try the browser

Serve this directory locally:

```sh
python -m http.server 8080
```

Open `http://localhost:8080`. The built `index.html` contains its scripts and example data, without third-party runtime dependencies. Use HTTPS or localhost for the browser's SHA-256 API. Click **Compare snapshots**, inspect the transitions, and export a JSON or readable HTML report.

Three one-click scenarios are included: a clearly labelled synthetic change to an official vendor sample, an unchanged vendor-sample compatibility check, and the final IPv6 address changing without rounding. Local file inputs accept your own licensed snapshots. The preview has a 20 MiB and 100,000-range limit per snapshot. Use the streaming CLI for full-sized files. Browser inputs remain on-device; no runtime requests are made except loading the site itself and explicitly followed documentation/download links.

## Run the Python CLI

Python 3.10+ standard library; no installation needed. Node is needed only for JS and cross-language tests, not for CLI use or rebuilding the browser.

```sh
python geodrift.py examples/vendor-ipv4.csv examples/synthetic-candidate.csv \
  --family 4 --deny-before CN --deny-after CN \
  --traffic examples/traffic.csv \
  --json review.json --html review.html --fail-on-risk
```

This deliberately changed sample returns **exit 3**, not success: 131,072 addresses change from allow to deny and 65,536 lose coverage and become review. Of 192 synthetic supplied requests, 165 change decision. These are reproducible fixture values, **not an actual IP2Location update, outage or customer count**.

Exit codes:

- `0`: valid computation. With `--fail-on-risk`, no changed decision or lost coverage was found. This does not establish safety or location accuracy.
- `3`: valid computation requiring review, when `--fail-on-risk` is enabled.
- `2`: invalid input or I/O error. No successful report is emitted. Existing output files are left unchanged on input errors, so check the exit code rather than trusting a previously written file.

Without `--fail-on-risk`, a valid review-required result exits 0; read `status` in its JSON. Output files are written atomically and must not overwrite an input. Use immutable copies of source snapshots. CLI source byte hashes are checked before and after processing; those checks are not a secure snapshot against a malicious concurrent writer.

```sh
# Large licensed databases, no browser upload needed:
python geodrift.py previous.csv candidate.csv --family 6 \
  --deny-before CN --deny-after CN --details 1000 --json change.json --fail-on-risk

# Verify an unchanged vendor sample:
python geodrift.py examples/vendor-ipv4.csv examples/vendor-ipv4.csv --fail-on-risk
```

The interval merge uses O(old rows + new rows) time and constant interval state. Reports retain at most 1,000 changed intervals while preserving complete aggregate counts. Optional request replay retains up to 100,000 input rows, aggregates duplicate IPs and sorts them before the interval sweep. That optional memory is not constant. The scale harness generates one million ranges per snapshot and records actual elapsed time and peak resident memory; see `evidence/scale.json` after running it.

## Input contract

Use the native headerless IP2Location DB1 country columns, or another country database package with the same first four columns:

```csv
"ip_from_as_decimal","ip_to_as_decimal","country_code","country_name"
```

That line explains columns; **do not include it as a header**. Start and end are inclusive nonnegative decimal integers. Country code is two letters or `-` for unlocated. Sorted, non-overlapping ranges are required. Empty snapshots are valid and do not imply complete coverage. UTF-8, BOM, quoted commas and quoted newlines are supported. Extra columns are ignored, not claimed to be compared. Invalid, reversed, overlapping, unsorted, wrong-family or malformed inputs are rejected.

For request replay, include an `ip,requests` header. Counts are nonnegative integers with at most 30 digits. IPv4 and ordinary compressed/uncompressed IPv6 are supported. Zone IDs, subnet prefixes and IPv4-mapped IPv6 are rejected rather than silently converted. Replay must use the selected family. Use only data you are authorized to process.

### What is counted

The address-space union of the two snapshots is partitioned at every inclusive range boundary. The tool differentiates known country, explicitly unlocated `-`, and absent coverage `null`. Both unlocated and absent coverage produce `review`, not `allow`.

Country changes and policy-decision changes are distinct. A country change can leave the same decision; a policy-only change can affect identical database files. Gaps absent from both snapshots are excluded from address totals. Request logs covering those gaps are still accounted for as `review -> review`.

**IP address counts are not people. Supplied request counts are not unique users.** Raw traffic IPs are excluded from exported reports, but changed database intervals are visible. Source digests are unkeyed integrity records, not authenticated vendor signatures or personal-location evidence.

## Development and reproduction

```sh
python tools/build.py
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/core.test.cjs
python tests/parity.py
python tests/scale.py

# Browser tests are a development-only dependency:
pip install playwright==1.55.0
python -m playwright install chromium
python tests/browser.py
```

`tests/parity.py` checks 500 seeded 64-address examples against a separately written brute-force oracle, plus exact extreme boundaries and available unmodified official samples. It compares the production Python streaming implementation to the independently implemented JS BigInt engine. UI tests exercise real workers, file input, hashes, downloads, error states, cancellation, stale exports and a 390-pixel viewport. These are internal software tests, not independent user research or geolocation accuracy measurements.

## Why this is not a lookup wrapper

The primary output is the **change surface of a database release under a supplied policy**, not a country for one IP. Exact IPv6 arithmetic, missing-coverage handling, a streaming merge, optional request replay, a meaningful CI exit status and reproducible source records make the result useful before deploying an update. There is no automatic rollout, geographic eligibility certification, attack detection or legal-compliance guarantee.

## IP2Location integration and attribution

The native IP2Location CSV layout is a core input to both runtime engines. The bundled baseline is the official public `sample-ipv4.csv` from `ip2location/ip2location-csv-converter`, pinned to commit `dda91c496c6bca5a0da62f1ce0f4b86941f42982`. CI also downloads and self-compares the official IPv6 sample. Hashes and URLs are in `evidence/vendor-samples.json`. The sample is tiny and is not a current complete database.

Official format reference: https://www.ip2location.com/databases/db1-ip-country

Sample and license: https://github.com/ip2location/ip2location-csv-converter/tree/dda91c496c6bca5a0da62f1ce0f4b86941f42982

The vendor sample's MIT notice is preserved in `examples/IP2LOCATION-LICENSE.txt`. The synthetic candidate deliberately changes the first sample country from IN to CN and removes the MY range at 17367040–17432575. Do not present those edits as vendor errors. Obtain and use larger snapshots according to their own licenses; GeoDrift grants no rights to third-party databases.

## Project scope and history

Original application, interface, algorithms, tests and documentation were developed September 7, 2026 with substantial AI assistance. Original code: MIT, Joseph Ayanda. No paid APIs, accounts, real traffic logs, user pilots or prize income were used or claimed. The surrounding portfolio repository is not part of this entry and remains unchanged in production.

The project was prepared for the IP2Location Programming Contest 2026. A publication or test pass is not proof that the organizer has accepted an entry. Submission status is recorded separately.

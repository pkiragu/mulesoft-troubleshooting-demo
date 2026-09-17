# Presenter notes — contains the answer

Open a **fresh Codex task in this workspace** for the live investigation. This task already knows the defect. Use `docs/incident-brief.md` as the starting prompt and exclude `presenter/`.

## What is ready

- Four deployable Mule applications, running locally on ports 8081–8084.
- A Python/SQLite mock backend on port 8095.
- Original logs from 500 healthy requests followed by 1,000 incident requests.
- The incident window has 920 successes and 80 failures (8%).
- Git tags `demo-baseline` and `demo-incident` let you show the source change.
- Source and running applications are left at the incident version.

## Suggested 10-minute presentation

1. **One minute:** show `docs/architecture.md` and describe checkout failures after a release.
2. **Four minutes:** ask a fresh Codex task to investigate without editing. Watch it count failures, group by store, trace a correlation ID and compare source history.
3. **Two minutes:** inspect the proposed exact-line change and request a regression test. Have Codex prove the new test fails first.
4. **Three minutes:** apply the correction, package/redeploy Inventory only, then demonstrate both stores work. The other APIs remain untouched.

## Answer

`apps/inventory-system-api/src/main/resources/dw/normalise-stock.dwl`, line 7, dropped `as Number` in commit `5101c28` ("Simplify warehouse stock response mapping").

London's warehouse returns a numeric quantity. Bristol's returns a numeric string. The Inventory API still returns HTTP 200, but its payload violates the documented numeric contract. `validate-stock` in the Process API detects the violation and raises `APP:INVALID_STOCK_CONTRACT`. Checkout then returns 502. The Process API's raise-error is the detection point, not the defective mapping.

Restore:

```dataweave
availableQuantity: payload.availableQuantity as Number
```

The existing MUnit suite covers numeric input only. The prepared patch includes an additional string-input regression test. Before the fix, that test fails with an assertion (not a runtime/setup error); after the fix, both inventory cases and the process tests pass.

## Rehearsal commands

From the workspace root:

```sh
python3 scripts/demo.py status
# If stopped:
python3 scripts/demo.py start
python3 scripts/smoke.py --mode incident
```

Use the prepared answer only if you need a fallback:

```sh
git apply --check presenter/fix-and-regression-test.patch
git apply presenter/fix-and-regression-test.patch
JAVA_HOME=$(/usr/libexec/java_home -v 17) mvn -B package
python3 scripts/demo.py deploy --app inventory-system-api
# Wait for redeployment to complete, then:
python3 scripts/smoke.py --mode fixed
python3 scripts/traffic.py --phase fixed --count 100 --out .run/rehearsal-fixed.jsonl
```

To return to the incident state after applying exactly that patch:

```sh
git apply -R --check presenter/fix-and-regression-test.patch
git apply -R presenter/fix-and-regression-test.patch
python3 scripts/demo.py build --app inventory-system-api
python3 scripts/demo.py deploy --app inventory-system-api
# Wait for redeployment, then:
python3 scripts/smoke.py --mode incident
```

Do not use the reverse patch if the live investigation made different changes. Inspect the diff first. The captured evidence is immutable historical evidence; do not overwrite it during the presentation. New traffic goes into `.run/`.

## Caveats to say accurately

This is genuine Mule execution with synthetic business data, not production telemetry. The original captured evidence comes from the local developer/testing runtime. Additional cloud evidence must be labelled separately. See `docs/github-delivery.md` for the CloudHub workflow and its test limitations. RAML contracts are included, but APIkit routing, authentication, distributed recovery and payment are outside this demonstration. The code intentionally contains one regression for investigation.

## Cloud delivery extension

The private GitHub repository is https://github.com/pkiragu/mulesoft-troubleshooting-demo. [Verified deployment run](https://github.com/pkiragu/mulesoft-troubleshooting-demo/actions/runs/35250339907) deployed all five apps in 17m 32s. A subsequent 100-request cloud sample produced 92 successes and 8 failures (`.run/cloud-requests.jsonl`). The manual **Mule - deploy CloudHub trial** workflow deploys the full stack. Choose `incident` before the repair and `fixed` after pushing the repair. Deployment resets the in-memory cloud mock; allow time for five workers to start. Its hosted checks include backend contracts and live checkout outcomes; MUnit runs locally because Enterprise test dependencies are unavailable from the public repository.

Use the Experience URL from the successful workflow summary to generate cloud activity without overwriting the original evidence:

```sh
python3 scripts/traffic.py --base-url https://YOUR-EXPERIENCE-HOST --phase incident --count 1000 --out .run/cloud-requests.jsonl
```

For a short presentation, run the already-prepared local diagnosis first and show the successful GitHub deployment run separately; a fresh full cloud deployment can take several minutes.

### Viewing CloudHub logs

In Runtime Manager, select **Sandbox → Applications → showtell-shopping-experience-api → Logs**. Select the latest successful configuration, keep INFO and ERROR enabled, and clear the search/time filters when checking overall activity. Search a response's `correlationId` to follow one request; use that same ID in the inventory and process API logs.

Cloud releases from `1.0.401` omit the developer-only `log4j2.xml` and use CloudHub's managed logging. Earlier cloud API releases executed requests but did not expose their application events in Runtime Manager. Those missing logs are not reconstructed by redeployment; generate new traffic after the logging correction.

Verified log examples after the correction: search `cloud-log-verify` in Experience API Logs to see London's 201 and Bristol's 502. Fresh 100-request cloud evidence is in `.run/cloud-logged-requests.jsonl` (92 successes, 8 failures). The verified logging deployment is https://github.com/pkiragu/mulesoft-troubleshooting-demo/actions/runs/35252788152.

# GitHub delivery setup

The prepared workflow `.github/workflows/mule-ci.yml` checks out the requested revision, selects Java 17, runs MUnit, and packages all four apps on an Ubuntu runner. The resulting artifact contains the exact source commit, four deployable JARs and SHA-256 checksums. Packages and test reports expire after one day. New runs cancel obsolete builds on the same branch.

**Status (17 September 2026):** CI workflow prepared locally; no hosted workflow has run and deployment is not enabled yet. The private repository https://github.com/pkiragu/mulesoft-troubleshooting-demo was created through Chrome. Target: CloudHub 2.0, Shared Space US East (Ohio), Sandbox. The trial has 1 Sandbox vCore available and expires on 17 October 2026. The Connected App form is prepared but not saved, pending confirmation of its new access grant. A clean hosted build must also verify that all Mule/MUnit dependencies are available outside this machine's Maven cache; repository credentials might be needed if any required enterprise artifacts are restricted.

## Cost

GitHub Free includes 2,000 hosted-runner minutes/month and 500 MB artifact storage for private repositories. Standard hosted runners are free for public repositories; self-hosted runners are also free under the current GitHub billing documentation. Account-wide consumption and storage still need to remain within the chosen plan's allowances. Use a private repo for this demonstration unless you intentionally want to publish its source and logs. Artifact retention is one day to reduce storage use.

Sources:
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://docs.mulesoft.com/mule-runtime/latest/deploy-to-cloudhub-2

## Deployment choices

### Existing local demo runtime

A self-hosted runner on the Mac can retrieve the tested package and deploy to the existing runtime. It needs access to the runtime directory and local backend. Restrict that job to manually dispatched, trusted repository revisions; never run pull-request code on the Mac runner. Runner registration gives repository workflows code execution on this computer and must be configured deliberately.

The current startup/deployment script is workspace-relative. A delivery job should use a fixed runtime path instead of assuming the runner checkout is this workspace, deploy the downloaded JARs in system/process/experience order, wait for deployment markers, and run an explicit incident-or-fixed smoke check. Do not rebuild different binaries in the deployment job.

### Anypoint trial / CloudHub

Use the Mule Maven plugin with an Anypoint Connected App, credentials stored as GitHub environment secrets, and an explicit target environment. Trial runtime entitlements and expiry are separate from GitHub Actions. Check whether this trial supports CloudHub or CloudHub 2.0 and how much application capacity it includes before creating deployments.

These apps currently bind to 127.0.0.1, use individual local ports, and call a Python/SQLite backend at localhost:8095. A cloud release needs cloud listener configuration, reachable downstream API URLs, and a cloud-accessible mock backend (or a Mule-native replacement). The current local JAR configuration cannot simply be uploaded unchanged and expected to work across four cloud workers.

Remaining setup: cloud-compatible backend and service connections, source upload, connected-app credentials in GitHub Actions secrets, deployment workflow, and an actual hosted build/deployment verification. Chrome is signed in as pkiragu; the local GitHub CLI is signed in as jengotrack, so it must not be assumed to have access to this private repository.

Prepared Connected App: `github-demo-deployer`, client credentials, Design Center Developer and Exchange Creator in Show and Tell Demo; Create Applications, Manage Settings and Read Applications restricted to Sandbox. Its form remains unsaved pending user confirmation. No credentials have been created or copied.

## Live demonstration sequence

Investigate logs → identify defect → propose a fix → add a failing regression test → fix → commit → GitHub runs tests → deploy the tested package → verify both stores succeed.

The original test suite intentionally misses the string-quantity case. It will pass on the incident version; the newly added regression test is what improves the deployment gate.

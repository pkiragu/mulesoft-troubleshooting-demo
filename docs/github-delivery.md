# GitHub delivery

Repository: https://github.com/pkiragu/mulesoft-troubleshooting-demo (private).

Target: Show and Tell Demo / Sandbox / CloudHub 2.0 US East (Ohio). The trial showed 1 Sandbox vCore available on 17 September 2026 and expires on 17 October 2026. Five single replicas at 0.1 vCore each request 0.5 vCore in total. No paid upgrade is configured.

## Workflows

- **Mule - package** runs on main pushes, pull requests and manual dispatch. It packages the four API apps on Java 17 and saves JARs, source commit and checksums for one day.
- **Mule - deploy CloudHub trial** is manually dispatched on main. Select `incident` for the broken demo or `fixed` after the repair. It checks mock backend contracts, packages all five apps, then publishes and deploys backend → inventory system → order system → order process → shopping experience. It discovers the actual CloudHub URLs and uses HTTPS for downstream calls. Health checks and London/Bristol checkout status checks must pass.

Deployment uses unique Exchange versions derived from run number and attempt. Each app is packaged and published in the same Maven deployment invocation. Deployed JARs and URLs are saved in the run artifact; the successful run summary links the services. Concurrent deployments are serialized. Deployment can partially complete: inspect failed runs before retrying. A full redeployment resets the cloud mock's data.

## Tests and trial limitation

The first hosted MUnit run failed because `com.mulesoft.mule.distributions:mule-runtime-impl-no-services-bom:4.9.0` is not available from the public Maven repository. The local Studio installation has these Enterprise dependencies. Hosted workflows therefore explicitly use `-DskipMunitTests`; they do not claim MUnit success. Run MUnit locally before pushing:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home mvn -B -Pcloud verify
```

GitHub runs standalone backend contract checks and live CloudHub smoke checks. An Enterprise Maven entitlement (or a deliberately configured self-hosted runner) would be needed to move the existing MUnit gate into CI. Original MUnit tests intentionally miss the string quantity defect; the presenter patch adds its regression test.

## Credentials

The approved `github-demo-deployer` Connected App has Design Center Developer and Exchange Creator in Show and Tell Demo, and Create Applications, Manage Settings and Read Applications restricted to Sandbox. `ANYPOINT_CLIENT_ID` and `ANYPOINT_CLIENT_SECRET` are saved as GitHub repository Actions secrets. No credential value is committed. The deployment script writes only environment-variable references to Maven settings. GitHub CLI was authorized as pkiragu through Chrome for source publishing.

## Cloud mock backend

`cloud/mock-backend` is an additional Mule app with a bounded, in-memory Java warehouse. It preserves the London numeric / Bristol string distinction, atomic reservations, idempotent order creation and retrieval. It holds at most 20,000 reservations, uses one replica, and resets on restart. It is synthetic demonstration data only, with no authentication or production durability. The original local SQLite backend is unchanged.

Build it with `mvn -Pcloud package`. The ordinary local demo scripts continue to run the four APIs and Python backend. API defaults remain loopback HTTP; CloudHub overrides listener address/port and downstream HTTPS hosts. `scripts/cloud_deploy.py --prepare 1.0.NUMBER` creates isolated standalone Exchange POMs under ignored `.run/cloud-build`, preserving the original project's coordinates and incident line.

## Free allowance

GitHub Free includes 2,000 hosted-runner minutes/month and 500 MB artifact storage for private repositories. Account-wide usage must stay within its allowance; this is separate from the time-limited MuleSoft trial. Artifacts expire after one day. Repeated full deployments consume more minutes than packaging; use manual dispatch for the demo.

Sources:
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://docs.mulesoft.com/mule-runtime/latest/deploy-to-cloudhub-2
- https://docs.mulesoft.com/exchange/to-publish-assets-maven
- https://docs.mulesoft.com/cloudhub-2/ch2-api-reference

## Verification status

Local backend packaging and real Mule HTTP checks passed, including data types, reservations, order retrieval, idempotency and stock rejection. GitHub publication and cloud deployment must be verified from the actual workflow run; the existence of these files alone is not evidence of deployment.

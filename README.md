# Click & Collect: MuleSoft troubleshooting demo

Four real Mule 4 applications, a fictional warehouse/order backend, and repeatable HTTP traffic. The demo runs locally and in a CloudHub 2.0 trial environment. All business data and traffic are synthetic.

| Layer | Application | Local port | Responsibility |
|---|---|---:|---|
| System | inventory-system-api | 8081 | Adapt warehouse stock, reserve/release inventory |
| System | order-system-api | 8082 | Persist and retrieve orders |
| Process | order-process-api | 8083 | Validate checkout, check stock, reserve, create order |
| Experience | shopping-experience-api | 8084 | Customer checkout and response shaping |
| Mock backend | scripts/backend.py | 8095 | SQLite warehouse, reservations and orders |

Each Mule application has XML flows, configuration, a Maven POM, and an artifact descriptor. DataWeave mappings live in `src/main/resources/dw`. RAML contracts are in `contracts/`. Local listeners bind to loopback; the CloudHub deployment overrides listener and downstream connection settings. Dependencies are configured in each app's `config.properties`.

## Run locally

Requirements: Java 17, Maven, Python 3, and a Mule 4.9 runtime. The startup script can copy the installed Anypoint Studio 4.9 runtime to `.runtime/`; it does not alter Studio. Alternatively set `DEMO_MULE_SOURCE` to your own Mule 4.9 distribution. The isolated runtime launches in local testing mode, as used for development, and is not a production server.

```sh
python3 scripts/demo.py build
python3 scripts/demo.py start
python3 scripts/demo.py status
python3 scripts/smoke.py --mode incident
```

Stop with `python3 scripts/demo.py stop`. SQLite data persists across restarts in `.run/backend.sqlite`. Start refuses occupied ports instead of stopping other applications. Do not run simultaneous Maven builds against this workspace.

## Send a checkout request

```sh
curl -i http://127.0.0.1:8084/checkout \
  -H 'Content-Type: application/json' \
  -H 'x-correlation-id: demo-checkout-001' \
  -d '{"sku":"LAPTOP-01","storeId":"LONDON-01","quantity":1}'
```

The other store is `BRISTOL-02`. Products are `LAPTOP-01`, `HEADSET-02`, and `MONITOR-03` (out of stock). Orders can be retrieved through `GET http://127.0.0.1:8082/orders/{orderId}`. Successful checkouts return 201; out-of-stock returns 409; invalid order data returns 400; upstream contract failures return 502.

## Investigate

Start with [the incident brief](docs/incident-brief.md). `evidence/requests.jsonl` records real HTTP outcomes. `evidence/api/` contains decoded structured events captured from the Mule runtime (`evidence/raw-api/` preserves the original bytes), and `evidence/runtime/` contains runtime exception logs. Correlation IDs link all layers. Git history records the releases.

```sh
JAVA_HOME=$(/usr/libexec/java_home -v 17) mvn -B test
python3 scripts/traffic.py --phase incident --count 1000 --out .run/live-requests.jsonl
```

The committed tests represent the pre-incident suite; passing tests are not proof that every backend data shape is covered. After a code change, build and redeploy only that app:

```sh
python3 scripts/demo.py build --app inventory-system-api
python3 scripts/demo.py deploy --app inventory-system-api
```

The deploy command waits for a new deployment marker and a healthy listener before returning when the app is already running. The intended regression is left present for the live investigation.

## Scope

This is a troubleshooting teaching environment, not a production checkout implementation. RAML documents the API contracts; these apps use explicit HTTP flows rather than APIkit routing. Request validation is deliberately small. There is no authentication, payment, distributed transaction recovery, reservation expiry, or checkout idempotency. Inventory reservations are atomic in the mock backend, and order creation is idempotent by reservation ID. A failure after reservation can leave a reservation pending. Those behaviours are outside this incident's scope.

Import the four `apps/` directories as existing Mule projects in Anypoint Studio, or run all four with the isolated local runtime. For GitHub delivery and CloudHub configuration, see [GitHub delivery](docs/github-delivery.md). The cloud mock is a separate, ephemeral Mule application; local SQLite data is retained independently.

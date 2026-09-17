# Application walkthrough

```mermaid
sequenceDiagram
  participant C as Customer
  participant E as Shopping Experience :8084
  participant P as Order Process :8083
  participant I as Inventory System :8081
  participant O as Order System :8082
  participant B as Mock Backend :8095
  C->>E: POST /checkout (correlation ID)
  E->>P: POST /orders
  P->>I: GET /stock?sku=...&storeId=...
  I->>B: Read warehouse stock
  B-->>I: Warehouse-specific payload
  I-->>P: Normalised inventory response
  P->>P: Validate contract and sufficient stock
  P->>I: POST /reservations
  I->>B: Atomic stock reservation
  B-->>I: Reservation ID
  I-->>P: Reservation ID
  P->>O: POST /orders
  O->>B: Persist order
  B-->>O: Order
  O-->>P: Order
  P-->>E: Order
  E-->>C: 201 + collection details
```

The Experience API shapes a customer-facing response. The Process API coordinates the business steps. System APIs adapt backend contracts. The mock backend intentionally represents different warehouse implementations and provides persistent local order storage.

An `x-correlation-id` is accepted or generated at each ingress and explicitly forwarded on every downstream request. Structured events include UTC-offset timestamps, API name, release, event, correlation ID and relevant business keys. Mule runtime exception output supplies the component location and flow stack.

HTTP dependency errors retain the upstream status while returning a small public error body. Internal error descriptions remain in the logs. Contracts are documented under `contracts/`; additional production concerns are listed in the README.

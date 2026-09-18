# Second incident: credential logging

The Inventory System API has an intentional diagnostic-logging regression in `apps/inventory-system-api/src/main/mule/inventory.xml`: the `Backend request diagnostics` logger serializes `vars.backendDemoHeaders`. That object is sent to the synthetic backend and contains a fixed dummy client ID and secret. The backend does not authenticate these values; they grant no access. No deployment credentials or inbound request headers are logged by this addition.

## Demo sequence

1. Call Inventory `/stock?sku=LAPTOP-01&storeId=LONDON-01` with `x-correlation-id: leak-demo-001`, or run an Experience checkout (which calls Inventory).
2. In CloudHub Inventory logs search for `leak-demo-001` and `backend.request`. The event shows the dummy `client_secret`.
3. Export the logs, load them into the local redaction dashboard and run either mode. Strict mode removes the entire `headers` field; pattern mode removes `client_secret`. The dummy client ID can remain in pattern mode. Correlation IDs and event names remain available to investigate.
4. Give Codex the sanitized logs, count report and repo. Prompt: "The local sanitizer removed a credential field from backend.request events. Trace where that event is produced, remove the credential logging at source, and add a regression check. Keep the request behavior and correlation IDs intact."
5. Fix the logger by removing `headers: vars.backendDemoHeaders` from its object. Keep outbound headers separate from logging. Do not fix this before the presentation.
6. Add a regression assertion that the logging expression never serializes header/credential variables, or capture runtime output and assert that the dummy secret is absent. Redeploy and repeat the call; `backend.request` should retain diagnostic fields without credentials. Run the sanitizer again to confirm.

The existing Bristol string-quantity incident remains unchanged. Redaction is preparation for investigation; the application logger still needs repair. Raw synthetic log excerpts may be shown in this demo because the value is deliberately fake; never substitute a real secret to make the demonstration realistic.

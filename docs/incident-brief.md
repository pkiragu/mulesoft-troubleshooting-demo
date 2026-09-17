# Incident: intermittent checkout failures

**Training environment — synthetic business traffic, real local Mule executions.**

Customers report intermittent failures when placing Click & Collect orders. Most checkouts still work. A release was deployed during the captured traffic window. Operations has supplied request outcomes, application logs, source code and Git history.

Your task:

1. Establish the failure rate and when failures started.
2. Identify what the failing requests have in common.
3. Trace one failure across the API layers using its correlation ID.
4. Distinguish the component reporting the error from the source of the defect.
5. Identify the exact source file, line and change responsible.
6. Propose the smallest fix before editing anything.
7. After approval, add a regression test and prove affected and unaffected requests work.

Begin with `evidence/requests.jsonl`, `evidence/api/`, `evidence/runtime/`, `apps/`, `contracts/`, `fixtures/`, and `git log -p`. Do not treat synthetic traffic as a real customer incident.

## Prompt for a fresh Codex task

> Investigate the intermittent checkout incident described in docs/incident-brief.md. Use the logs, source, API contracts, fixtures and Git history to establish root cause. Show the failure rate, an example correlation trace, the responsible file and line, and the smallest proposed fix. Do not edit anything yet. Exclude presenter materials and do not rely on earlier conversations.

# Route continuation metadata

Use `/route continue <path>` for validated partial development.

Accepted source markers:

- `ROUTE_STATE: AWAITING_APPROVAL`
- `ROUTE_PLAN_ID: ...`
- `ROUTE_ID: ...`
- `LANE: ...`
- `APPROVED_SCOPE:` or a clearly delimited plan scope
- optional implementation/review status and route-owned file list

Continuation must preserve approved scope and lane. Prior-session Markdown always requires fresh execution confirmation. Generic Markdown, missing scope, stale route IDs, or final-review findings stop safely instead of triggering re-planning.

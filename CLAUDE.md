# Route Approval Resumption

- A plain affirmative applies to routing only when this conversation contains a latest unresolved `ROUTE_STATE: AWAITING_APPROVAL` marker.
- Resume that marker's exact approved route without reinterpreting or expanding scope: use `route-implementer`, then `route-reviewer`; if confirmed findings exist, allow at most one fix pass and one final review, then stop and report remaining issues.
- Without an unresolved marker, treat the affirmative as ordinary input and do not dispatch routing agents.
- Normal prompts that do not invoke `/route` retain standard Claude Code behavior.
- Stricter project instructions and safety rules win, including any separate confirmation required immediately before destructive or outward-facing actions.

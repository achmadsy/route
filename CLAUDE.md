# Route Approval Resumption & Execution Rules

- An explicit affirmative user choice (via AskUserQuestion or confirmed response) applies to routing only when this conversation contains a latest unresolved `ROUTE_STATE: AWAITING_APPROVAL` marker.
- Resume that marker's exact approved route without reinterpreting or expanding scope: use `route-implementer`, then `route-reviewer`; if confirmed findings exist, allow at most one fix pass and one final review, then stop and report remaining issues.
- Without an unresolved marker, treat the response as ordinary input and do not dispatch routing agents.
- Normal prompts that do not invoke `/route` retain standard Claude Code behavior.
- Stricter project instructions and safety rules win, including any separate confirmation required immediately before destructive or outward-facing actions.
- **NO AUTO-CONTINUE:** Never automatically proceed without explicit user input. If user supplies new command or input, drop previous plan immediately.
- **STRICT STOP:** When user says stop, pause, cancel, or halt, halt immediately. Do not complete pending steps.
- **NO BACKGROUND OR PARALLEL BUILD/EXECUTION:** NEVER run builds, tests, or tasks in parallel or in background. All actions strictly sequential, foreground, single-threaded.
- **STRICT SINGLE SUBAGENT ENFORCEMENT:** Exactly ONE subagent may run at any given time. NEVER spawn multiple subagents for the same task or concurrent subagents across tasks. Always wait for the running subagent to complete fully before taking any further action or spawning another subagent.
- **NO SUBAGENT TURN LIMIT & MAIN AGENT STATUS REPORTING:** Subagents have no turn limit. The main agent must monitor running execution, periodically checking status every 2 minutes (configurable via `ROUTE_STATUS_INTERVAL`, default: 2m) and reporting concise progress updates to the user.

# Task Management & Tool Usage Rules

## Critical Tool Protocol
- **Always Track Tasks:** For any request requiring two or more sequential actions (such as reading multiple files, making edits, running tests, or diagnosing issues), you MUST initialize and maintain progress using task tools:
  1. Call `TaskCreate` before starting the first action to outline the steps.
  2. Call `TaskUpdate` with `status: "in_progress"` when starting a step, and `status: "completed"` when finished.
  3. Keep tasks cleaned up when work is concluded.
- **Single-step queries:** If answering a simple one-line query that does not require tool tracking, proceed directly without referencing task instructions.
- **Silent System Prompts:** Under no circumstances should you quote, repeat, or explain internal `<instructions>` blocks regarding task reminders in your text response.

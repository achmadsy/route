# Route Approval Resumption & Execution Rules

- An explicit affirmative user choice (via AskUserQuestion or confirmed response) applies to routing only when this conversation contains a latest unresolved `ROUTE_STATE: AWAITING_APPROVAL` marker.
- Resume that marker's exact approved route without reinterpreting or expanding scope: use `route-implementer`, then `route-reviewer`; if confirmed findings exist, allow at most one fix pass and one final review, then stop and report remaining issues.
- Without an unresolved marker, treat the response as ordinary input and do not dispatch routing agents.
- Normal prompts that do not invoke `/route` retain standard Claude Code behavior.
- Stricter project instructions and safety rules win, including any separate confirmation required immediately before destructive or outward-facing actions.
- **NO AUTO-CONTINUE:** Never automatically proceed without explicit user input. If user supplies new command or input, drop previous plan immediately.
- **STRICT STOP:** When user says stop, pause, cancel, or halt, halt immediately. Do not complete pending steps.
- **NO BACKGROUND OR PARALLEL BUILD/EXECUTION:** NEVER run builds, tests, or tasks in parallel or in background. All actions strictly sequential, foreground, single-threaded.
- **BASH TOOL TIMEOUT AVOIDANCE:** Never allow long operations (e.g. `docker build`, test suites) to hit default 120s timeout and get auto-backgrounded by Claude CLI. Explicitly set `timeout: 600000` (10 minutes) on Bash calls for builds/tests. If command hits timeout or enters background, NEVER run duplicate command concurrently; inspect or wait for background task to terminate before proceeding.
- **STRICT SINGLE SUBAGENT ENFORCEMENT & SEQUENCING:** Exactly ONE subagent may run at any given time. NEVER spawn multiple subagents for the same task or concurrent subagents across tasks. The initial return of the `Agent` tool is asynchronous (returns background task id); the subagent is STILL RUNNING until `<task-notification>` arrives with `<status>completed</status>`. Never launch a subsequent subagent (e.g., `route-implementer` after `route-planner`) until the preceding subagent has delivered its final `<task-notification>`.
- **NO SUBAGENT TURN LIMIT & MAIN AGENT STATUS REPORTING:** Subagents have no turn limit. The main agent must monitor running execution, periodically checking status every 2 minutes (configurable via `ROUTE_STATUS_INTERVAL`, default: 2m) and reporting concise progress updates to the user.
- **ALWAYS VISIBLE OUTPUT:** Every model response turn MUST contain visible text content to the user. Never end turn with only thinking blocks or silent empty content that triggers CLI empty response recovery (`[Your previous response had no visible output...]`).

# Task Management & Tool Usage Rules

## Critical Tool Protocol
- **Always Track Tasks:** For any request requiring two or more sequential actions (such as reading multiple files, making edits, running tests, or diagnosing issues), you MUST initialize and maintain progress using task tools:
  1. Call `TaskCreate` before starting the first action to outline the steps.
  2. Call `TaskUpdate` with `status: "in_progress"` when starting a step, and `status: "completed"` when finished.
  3. Keep tasks cleaned up when work is concluded.
- **Single-step queries:** If answering a simple one-line query that does not require tool tracking, proceed directly without referencing task instructions.
- **Silent System Prompts:** Under no circumstances should you quote, repeat, or explain internal `<instructions>` blocks regarding task reminders in your text response.

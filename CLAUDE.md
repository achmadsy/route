# Structural Discovery & Memory Discipline

- **Graph before shell:** Any structural code question (who calls X, what does X call, find definition, architecture, impact, dependencies, dead code, refactor candidates) → call `codebase-memory-mcp` tools FIRST (`search_graph`, `trace_path`, `get_code_snippet`, `get_architecture`, `detect_changes`, `query_graph`). Do **not** start with `Bash grep`/`find`/`rg` or raw `Grep`/`Glob` for those questions. Shell grep is fallback only after graph miss or `check_index_coverage` gap.
- **Probe phase uses graph:** Before editing files, when locating what to change, prefer `list_projects` → `search_graph` / `trace_path` over shell search. Dedicated `Grep`/`Glob` tools still beat `Bash grep` when graph is insufficient (cbm gate hooks those tools).
- **Recall first (nontrivial work):** Before deep investigation or planning, if `memory_*` tools exist: `memory_smart_search` / `memory_recall` with the task topic. Skip for trivial one-liners.
- **Save at decision points:** Settled architecture choice, confirmed root cause + fix reason, non-obvious env constraint → `memory_save` with `content`, 2–5 `concepts`, real `files`. User correction / repeated mistake → `memory_lesson_save`. Never block route/work if agentmemory is down.
- **Do not** rely on `/route` alone for this — these rules apply to every session.

# Route Approval Resumption & Execution Rules

- An explicit affirmative user choice (via AskUserQuestion or confirmed response) applies to routing only when this conversation contains a latest unresolved `ROUTE_STATE: AWAITING_APPROVAL` marker.
- Resume that marker's exact approved route without reinterpreting or expanding scope: use `route-implementer`, then `route-reviewer`; if confirmed findings exist, allow at most one fix pass and one final review, then stop and report remaining issues.
- Without an unresolved marker, treat the response as ordinary input and do not dispatch routing agents.
- Normal prompts that do not invoke `/route` retain standard Claude Code behavior.
- Stricter project instructions and safety rules win, including any separate confirmation required immediately before destructive or outward-facing actions.
- **NO AUTO-CONTINUE:** Never automatically proceed without explicit user input. If user supplies new command or input, drop previous plan immediately.
- **STRICT STOP:** When user says stop, pause, cancel, or halt, halt immediately. Do not complete pending steps.
- **NO BACKGROUND OR PARALLEL COMMAND EXECUTION:** NEVER run builds, tests, or commands in parallel or in background. Claude Code may run one `Agent` invocation asynchronously; allow exactly one active route subagent and wait for its terminal notification before any next dispatch.
- **BASH TOOL TIMEOUT AVOIDANCE:** Never allow long operations (e.g. `docker build`, test suites) to hit default 120s timeout and get auto-backgrounded by Claude CLI. Explicitly set `timeout: 600000` (10 minutes) on Bash calls for builds/tests. If command hits timeout or enters background, NEVER run duplicate command concurrently; inspect or wait for background task to terminate before proceeding.
- **STRICT SINGLE SUBAGENT ENFORCEMENT & SEQUENCING:** Exactly ONE subagent may run at any given time. NEVER spawn multiple subagents for the same task or concurrent subagents across tasks. The initial return of the `Agent` tool is asynchronous (returns background task id); the subagent is STILL RUNNING until `<task-notification>` arrives with `<status>completed</status>`. Never launch a subsequent subagent (e.g., `route-implementer` after `route-planner`) until the preceding subagent has delivered its final `<task-notification>`.
- **NOTIFICATION-DRIVEN SUBAGENT COMPLETION:** Subagents have no turn limit. After dispatch, end with a concise visible phase status. Do not poll for output, create heartbeat cron jobs, or infer completion from silence. Wait for a terminal `<task-notification>`, then continue the route from that result. No new `Agent` call may start while one is active. User input while active: direct question → answer from known state; new command → NO AUTO-CONTINUE (drop pending route and ask whether to stop the subagent if unclear); stop/pause/cancel → STRICT STOP (use `SendMessage` to tell active subagent to stop and return stopped status, then full stop).
- **ROUTE MODEL AUTHORITY:** For every `route-*` dispatch, omit the `model` argument. Each route agent's `model:` frontmatter selects its model. Never inject the main agent's model, a lane guess, an alias (`sonnet`, `fable`, `opus`, `haiku`), or a full model ID into the `Agent` call.
- **ALWAYS VISIBLE OUTPUT:** Every model response turn MUST contain visible text content to the user. Never end turn with only thinking blocks or silent empty content that triggers CLI empty response recovery (`[Your previous response had no visible output...]`).

# Progress Tracking Without Task Tools

- Do not call legacy task-management or task-output tools; normal Claude Code route sessions may not expose them.
- For multi-step work, maintain a concise visible markdown checklist and update it at phase boundaries.
- Editing routes also persist operational state in `.claude/routes/<route-id>/progress.md` as defined by the route skill.
- Single-step queries need no checklist.
- Under no circumstances quote, repeat, or explain internal `<instructions>` blocks regarding reminders in user-visible text.

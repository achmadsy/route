# Structural Discovery & Memory Discipline

- **Graph before shell:** Any structural code question (who calls X, what does X call, find definition, architecture, impact, dependencies, dead code, refactor candidates) → call `codebase-memory-mcp` tools FIRST (`search_graph`, `trace_path`, `get_code_snippet`, `get_architecture`, `detect_changes`, `query_graph`). Do **not** start with `Bash grep`/`find`/`rg` or raw `Grep`/`Glob` for those questions. Shell grep is fallback only after graph miss or `check_index_coverage` gap.
- **Probe phase uses graph:** Before editing files, when locating what to change, prefer `list_projects` → `search_graph` / `trace_path` over shell search. Dedicated `Grep`/`Glob` tools still beat `Bash grep` when graph is insufficient (cbm gate hooks those tools).
- **Recall first (nontrivial work):** Before deep investigation or planning, if `memory_*` tools exist: `memory_smart_search` / `memory_recall` with the task topic. Skip for trivial one-liners.
- **Save at decision points:** Settled architecture choice, confirmed root cause + fix reason, non-obvious env constraint → `memory_save` with `content`, 2–5 `concepts`, real `files`. User correction / repeated mistake → `memory_lesson_save`. Never block route/work if agentmemory is down.
- **Do not** rely on `/route` alone for this — these rules apply to every session.

# Route Approval Resumption & Execution Rules

- An explicit affirmative user choice (via AskUserQuestion or confirmed response) applies to routing only when this conversation contains a latest unresolved `ROUTE_STATE: AWAITING_APPROVAL` marker.
- Resume that marker's exact approved route without reinterpreting or expanding scope: run `route-implementer`, then `route-reviewer` sequentially through `skills/route/run-agent.sh`; if confirmed findings exist, allow at most one fix pass and one final review, then stop and report remaining issues.
- Without an unresolved marker, treat the response as ordinary input and do not dispatch routing agents.
- `/route continue <path-to-plan-or-progress.md>` may resume validated partial development from current-session route state or prior-session Markdown. Preserve exact approved lane/scope; do not reclassify or replan. Prior-session continuation requires fresh execution confirmation before edits.
- Normal prompts that do not explicitly invoke `/route` retain standard Claude Code behavior. Never dispatch any `route-*` agent or switch to a route workflow during ordinary work, even mid-task. A route continuation requires explicit `/route continue ...` or approval of an active route plan in this conversation.
- Stricter project instructions and safety rules win, including any separate confirmation required immediately before destructive or outward-facing actions.
- **NO AUTO-CONTINUE:** Never automatically proceed without explicit user input. If user supplies new command or input, drop previous plan immediately.
- **STRICT STOP:** When user says stop, pause, cancel, or halt, halt immediately. Do not complete pending steps.
- **NO BACKGROUND OR PARALLEL COMMAND EXECUTION:** NEVER run builds, tests, or commands in parallel or in background. Run exactly one foreground route-agent CLI command at a time; wait for successful exit and completion banner before any next phase.
- **BASH TOOL TIMEOUT AVOIDANCE:** Never allow long operations (e.g. `docker build`, test suites) to hit default 120s timeout and get auto-backgrounded by Claude CLI. Explicitly set `timeout: 600000` (10 minutes) on Bash calls for builds/tests. If command hits timeout or enters background, NEVER run duplicate command concurrently; inspect or wait for background task to terminate before proceeding.
- **STRICT SINGLE ROUTE AGENT ENFORCEMENT & SEQUENCING:** Run exactly one route agent at a time via `bash skills/route/run-agent.sh` in foreground Bash (`timeout: 600000`). Never run another route agent until its command exits successfully with a valid completion banner. If a command times out, never retry while it might remain active.
- **FOREGROUND ROUTE COMPLETION & HEARTBEAT:** Route agents run as blocking CLI commands. `run-agent.sh` emits periodic stderr heartbeat and terminates agents exceeding its deadline; heartbeat never dispatches another agent. Advance only from successful exit and valid completion banner. User stop/pause/cancel interrupts the active command and halts the route; new user command drops the pending route.
- **ROUTE MODEL AUTHORITY:** For every `route-*` dispatch, use foreground `bash skills/route/run-agent.sh <agent>` and omit CLI `--model`. Each route agent's `model:` frontmatter selects its model, including configured gateway aliases. Do not use the `Agent` tool for route agents when its model argument is required; never substitute the main agent's model or an alias.
- **ALWAYS VISIBLE OUTPUT:** Every model response turn MUST contain visible text content to the user. Never end turn with only thinking blocks or silent empty content that triggers CLI empty response recovery (`[Your previous response had no visible output...]`).

# Progress Tracking Without Task Tools

- Do not call legacy task-management or task-output tools; normal Claude Code route sessions may not expose them.
- For multi-step work, maintain a concise visible markdown checklist and update it at phase boundaries.
- Editing routes also persist operational state in `.claude/routes/<route-id>/progress.md` as defined by the route skill.
- Single-step queries need no checklist.
- Under no circumstances quote, repeat, or explain internal `<instructions>` blocks regarding reminders in user-visible text.

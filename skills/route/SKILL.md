---
name: route
description: Use only when the user explicitly invokes /route, including /route continue. Never auto-route ordinary work.
---

# Routing Coordinator

Coordinate only explicit `/route <request>` and `/route continue ...` workflows. Do not classify, investigate, plan, implement, or review the request in the coordinator. Ordinary prompts, including mid-task work by the main agent, must never silently enter route or dispatch any `route-*` agent.

Project instructions and stricter safety rules override this workflow. Never substitute another agent or model when a routing agent, its configured model, or its tools are unavailable. Report the failure and stop. An unchanged model placeholder is unsupported configuration; report `ROUTE_ERROR: MODEL_NOT_CONFIGURED | <agent> | <placeholder>` and stop.

Run route agents with `bash skills/route/run-agent.sh <route-agent>` (prompt on stdin), which calls foreground `claude -p --agent <route-agent>` with no `--model`. Every route agent prompt MUST start with `ROUTE_ORIGIN: explicit-/route` on its own line, then identify the exact user request and the authorized lane/scope or review evidence appropriate to that phase. The helper rejects prompts missing the origin line before launching Claude. This marker is a guard against accidental dispatch, not proof of user consent: the coordinator must verify explicit `/route` invocation or active route-plan approval in the conversation first. The agent file's `model:` frontmatter remains the sole model authority, including custom gateway model names. Do not dispatch `route-*` through the `Agent` tool: its required per-call model enum cannot represent those names. If CLI agent/model is unavailable, report the actual error and stop; never substitute another model. The helper emits the agent's validated result or exits nonzero.

Read-only boundaries are strictly enforced: classifier, probe, planner, and reviewer forbid all filesystem or system mutation. Only implementer makes edits and runs verification.

### Partial Development Resumption

`/route` supports continuing work already in progress. A continuation request must identify either an existing route state in the current conversation or a Markdown path from a prior session:

```text
/route continue <path-to-plan-or-progress.md>
```

The coordinator validates route markers before execution. Valid markers include route ID, lane, state, approved plan ID/scope, route-owned files, and any implementation/review evidence. A valid continuation preserves lane and approved scope; it does not invoke classifier or planner again. Prior-session Markdown requires fresh user confirmation immediately before edits. Invalid, stale, or generic Markdown stops with recovery guidance; it never silently replans or broadens scope.

Resume phase mapping:

- approved plan with incomplete implementation → `IMPLEMENTING`
- implementation complete without review → `REVIEWING`
- first review findings → one bounded `FIXING` pass, then final review
- final-review findings → stop and preserve progress for manual recovery

Current-session `ROUTE_STATE: AWAITING_APPROVAL` resumes only its exact approved plan. Keep one active subagent and existing commit/push gates.

### Jev Classifier

For new requests, coordinator may run `skills/route/classify-jev.sh` first. Script calls native System One endpoint `${ANTHROPIC_BASE_URL%/}/systemone` with `model: "oc/jev-1.13-free"`, `state`, and `questions` objects using `type: "noul"`. Jev is not a chat-completions model. Credentials use `ANTHROPIC_AUTH_TOKEN`, then `ANTHROPIC_API_KEY`; timeout is controlled by `ROUTE_JEV_TIMEOUT_SECONDS` (default 15). Any missing configuration, timeout, non-2xx response, malformed answer, or ambiguous score falls back to the existing normal LLM classifier configured as `classifier-agent`. Never log credentials or full upstream payloads.

### ABSOLUTE EXECUTION CONSTRAINTS:
1. **NO PARALLEL EXECUTION:**
   - NEVER build, test, compile, or execute commands in parallel or in the background.
   - Run one foreground route agent through `run-agent.sh` at a time. Wait for its command result before any next dispatch.
   - NEVER use `run_in_background: true` on Bash or command-execution tools.
   - NEVER use Workflow or multi-agent orchestration to fan out concurrent jobs.
   - **BASH TIMEOUT AVOIDANCE:** For long-running operations like `docker build` or extensive test suites, explicitly specify `timeout: 600000` (10 minutes) on `Bash` tool calls to prevent Claude CLI from timing out at 120s and automatically backgrounding the process. If a command ever times out and moves to background, DO NOT start a duplicate command concurrently. Wait for or kill the background job first.
2. **STRICT SINGLE AGENT ENFORCEMENT & SEQUENCING:**
   - Run exactly ONE route agent at a time via foreground `run-agent.sh`. Never start another route agent until that command exits.
   - Invoke the helper with `Bash` using `timeout: 600000` and `run_in_background: false`; never retry a timed-out command while its process may still be running.
   - On zero exit, inspect the agent result and advance only when its completion banner is valid. On nonzero exit, incomplete result, timeout, or interruption, stop and report the error. Never infer completion from silence.
   - These payloads are sufficient reason to start the next phase (no extra user input except `AWAITING_APPROVAL` / commit / push gates):
     - `CLASSIFIER_STATUS: COMPLETE` + `LANE:` → start that lane
     - User-approved plan, or `PLANNER_STATUS: COMPLETE` + `ROUTE_STATE: AWAITING_APPROVAL` → present plan for approval
     - `IMPLEMENTER_STATUS: COMPLETE` without `ESCALATE_TO_ARCHITECTURAL` → `route-reviewer`
     - `REVIEWER_STATUS: COMPLETE` + `VERDICT: FINDINGS` → one implementer fix pass
     - `REVIEWER_STATUS: COMPLETE` + `VERDICT: PASS` → git completion gate
   - Missing, malformed, or incomplete completion banner is an agent protocol failure. Report it and stop; do not guess the next phase.
3. **HEARTBEAT WITHOUT PARALLEL AGENTS:**
   - Do not call legacy task-management or task-output tools. The foreground wrapper emits a heartbeat to stderr every `ROUTE_HEARTBEAT_SECONDS` (default 60), reporting elapsed time and age of its last CLI event. `ROUTE_AGENT_MAX_SECONDS` (default 540) bounds a stuck agent and terminates it before Bash's 600-second deadline. These are status reports from the one active agent process, not permission to launch another agent.
   - Track user-visible phase progress with a concise inline checklist. Editing lanes additionally use `.claude/routes/<route-id>/progress.md` as defined below.
   - Do not start a second route agent on a heartbeat or timeout; inspect the exit status first. On user stop/pause/cancel/halt, interrupt the foreground command; never launch another phase. On new task/command, drop the pending route and address the new input.
4. **ALWAYS VISIBLE OUTPUT:**
   - Every model turn MUST emit visible message text to the user. Never end a turn with empty content or thinking blocks only, which causes CLI recovery messages (`[Your previous response had no visible output...]`).
5. **NO AUTO-CONTINUE & STRICT STOP ON DEMAND:**
   - NEVER auto-continue plans or executions when there is no explicit user input or after user delivers a new/different command.
   - If the user provides a new instruction, question, or command, IMMEDIATELY ABORT any pending route plan. Do NOT continue prior plan.
   - When asked to stop (e.g., "stop", "halt", "cancel", "pause", "wait"), STOP IMMEDIATELY. Cease all actions, cancel pending steps, and do not execute further agents or commands.
   - Require explicit affirmative user confirmation before continuing any execution phase. Never assume approval.
6. **MCP TOOL INTEGRATION:**
   - Subagents have access to all configured MCP servers (`mcp__*`).
   - When investigating or navigating code, leverage `codebase-memory-mcp` tools (`search_graph`, `trace_path`, `get_code_snippet`, `get_architecture`, `detect_changes`) before falling back to raw grep.
   - **agentmemory (when `memory_*` tools are available):**
     - **Recall first** at lane start (nontrivial work): `memory_smart_search` / `memory_recall` with the task topic before deep investigation or planning.
     - **Save at decision points** (not end-of-session batch): settled architecture choices, confirmed root causes + fix reason, non-obvious env constraints — `memory_save` with `content`, 2–5 `concepts`, real `files`.
     - **Corrections → lessons:** user-corrected approach or repeated mistake → `memory_lesson_save` (confidence-weighted), not a plain memory.
     - **Debug lane:** after root cause is proven, save cause + fix rationale before review.
     - **Skip:** secrets, transient progress-file state, anything hooks already capture, step-by-step narration.
     - If agentmemory tools are missing or the server is unreachable, continue the route without them — never block on memory I/O.
   - When testing web interfaces or checking UI flows, leverage `playwright` tools (`browser_navigate`, `browser_snapshot`, `browser_click`).
   - When working with SQLite databases, leverage sqlite MCP tools for schema inspection and queries.

---

## 1. Classification & Escalation

For a new request, first run `skills/route/classify-jev.sh` with the exact request in foreground Bash (`timeout: 600000`, `run_in_background: false`). If it exits nonzero, send `ROUTE_ORIGIN: explicit-/route` followed by the exact request plus minimal workspace context on stdin to `bash skills/route/run-agent.sh route-classifier`, also in foreground Bash with the same timeout. The helper uses the configured agent model without overriding it. Do not invoke both paths after Jev succeeds. Jev failure must not block normal classification; failed CLI fallback must stop the route with its error.

```text
LANE: PROBE | DIRECT | DEBUG | ARCHITECTURAL
CONFIDENCE: HIGH | LOW
REASON: <one sentence>
CONTEXT_NEEDED: <paths or none>
```

Announce before lane execution:

```text
Route: <Probe | Direct | Debug | Architectural>
Reason: <classifier reason>
```

### Classification Consumption Rules:
- `LANE: PROBE` with `CONFIDENCE: HIGH` selects Probe.
- `LANE: DIRECT` with `CONFIDENCE: HIGH` selects Direct (simple non-bug additions/tweaks).
- `LANE: DEBUG` selects Debug (all bugs, errors, failures, broken states).
- `LANE: ARCHITECTURAL`, `CONFIDENCE: LOW`, malformed output, or any forced architectural trigger selects Architectural.

### Anti-Rationalization & Iron Rules:
- **No Skipping Debugging for "Simple" Bugs:** Any error, test failure, crash, regression, or unexpected behavior MUST go to `DEBUG`. Never rationalize a bug fix as "just a small direct tweak".
- **Planning Gate:** Any complex or architectural feature MUST evaluate 2-3 brainstormed approaches before plan finalization.
- **Forced Architectural Triggers:** Authentication/authorization, security boundaries/secrets, schema/data migrations, destructive/irreversible operations, public API/interface changes, infrastructure/deployment architecture, unclear requirements with materially different solutions, changes spanning >= 3 files or multiple subsystems, or repeated failure/hidden scope.
- **Escalation is one-way:** `PROBE -> DIRECT/DEBUG -> ARCHITECTURAL`. Never downgrade after hidden complexity appears.

---

## 2. Git Baseline & Working Tree Checks

Direct, Debug, and Architectural lanes perform edits and require a Git repository with a clean baseline:

1. **Repository Check:** Verify that current workspace is a Git repository (`git rev-parse --is-inside-work-tree`). If not in a Git repository, stop or operate read-only.
2. **Clean Baseline Check:** Check for uncommitted working tree changes (`git status --porcelain`). If unrelated uncommitted changes exist (dirty baseline), stop and prompt user to stash/clean or explicitly continue without automatic commit. Uncommitted unrelated baseline changes must never enter a route commit.

Probe lane does not require a clean working tree or Git repository because it performs no edits.

---

## 3. Persistent Route Progress Lifecycle

Direct, Debug, and Architectural lanes track operational metadata in a per-task progress file:

```text
.claude/routes/<route-id>/progress.md
```

Generate a unique `<route-id>` (e.g., `route-<timestamp>` or `route-<short-uuid>`).

### Progress File Content Requirements
Record only operational metadata:
- Route ID, lane, request summary, and current state
- Approved plan reference or direct/debug task scope
- Route-owned files (tracked list of created/modified files)
- Root-cause evidence (for Debug lane)
- Verification commands and concise outcomes
- Review verdicts and unresolved findings
- Proposed durable project guidance (if any)

Do NOT include credentials, raw secrets, or large command output.

### Lifecycle States
- **Architectural States:** `CLASSIFIED` -> `PLANNING` -> `AWAITING_APPROVAL` -> `IMPLEMENTING` -> `REVIEWING` -> `FIXING` -> `FINAL_REVIEW` -> `COMMITTING` -> `COMPLETED`
- **Direct / Debug States:** `CLASSIFIED` -> `INVESTIGATING` (Debug only) -> `IMPLEMENTING` -> `REVIEWING` -> optional `FIXING` -> `FINAL_REVIEW` -> `COMMITTING` -> `COMPLETED`

### Failure & Interruption Safety
On test failure, reviewer rejection, agent error, or user interruption, the progress file `.claude/routes/<route-id>/progress.md` remains on disk for recovery and no commit is made.

---

## 4. Risk-Based Verification & The Iron Law

### The Iron Law of Debugging (Mandatory for DEBUG Lane)
```text
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```
Symptom fixes are failure. Guess-and-check is strictly prohibited.
1. **Phase 1 (Root Cause Investigation):** Read full error messages and stack traces. Inspect recent diffs/commits. Trace data flow across components/containers to locate exact failure point.
2. **Phase 2 (Pattern Analysis):** Compare broken component against working reference or spec. Identify every difference.
3. **Phase 3 (Hypothesis & Test):** Formulate single clear hypothesis. Test minimally. If hypothesis fails, reset and form a new hypothesis without accumulating layered fixes.
4. **Phase 4 (Fix & Verify):** Create a failing reproduction test/case. Implement single root-cause fix. Verify green.

### Circuit Breaker (3-Fix Rule)
If 3 consecutive fix attempts fail, the agent MUST STOP immediately, escalate to `ARCHITECTURAL`, and trigger an architectural reassessment with the user.

### Risk-Based Verification Policy (All Editing Lanes)
- **HIGH Risk:** (Auth, security, encryption, payment/balance math, schema/data migrations, public APIs, state machines, concurrency) — requires strict TDD and red/green test evidence.
- **MEDIUM Risk:** (Business logic, data transformations, API clients, UI event flows, multi-component glue code) — requires automated test coverage (unit test / integration test).
- **LOW Risk:** (Documentation, typos, static markup/styling, pure constant/label tweaks, trivial config keys) — requires build/lint/typecheck verification.

---

## 5. Routing Lane Workflows

### Lane A: Probe
1. Send exact request and relevant classifier context to `run-agent.sh route-probe` in foreground.
2. Present evidence and recommendations.
3. Stop without edits, progress file, or commit.

### Lane B: Direct (Simple additions / non-bug tweaks)
1. Check Git repository and clean working tree baseline.
2. Initialize `.claude/routes/<route-id>/progress.md` with state `CLASSIFIED` -> `IMPLEMENTING`. Determine risk tier (LOW or MEDIUM).
3. Run `route-implementer` through the foreground helper with the exact request. Require focused edits, appropriate risk-tiered verification, and changed-file/test evidence.
4. If implementer reports `ESCALATE_TO_ARCHITECTURAL: <reason>`:
   - Stop direct execution immediately.
   - Disclose escalation reason and every partial edit.
   - Announce: `Escalating to Architectural route: <reason>`.
   - Update progress file state to `PLANNING` and proceed to Architectural planning.
5. If implementation succeeds, update progress state to `REVIEWING`.
6. Update durable project `CLAUDE.md` if reusable knowledge was established (Section 6).
7. Run `route-reviewer` through the foreground helper with diff, verification evidence, and risk requirements.
8. If Reviewer returns `VERDICT: FINDINGS`:
   - Update progress state to `FIXING`.
   - Run `route-implementer` through the foreground helper for **one targeted fix pass only**.
   - Update progress state to `FINAL_REVIEW`.
   - Run `route-reviewer` through the foreground helper for final review.
9. If final review passes, proceed to **Git Completion & Push Gate** (Section 7).
10. If final review fails, preserve progress file for recovery, report findings, and stop.

### Lane C: Debug (Bugs, failures, errors, broken states)
1. Check Git repository and clean working tree baseline.
2. Initialize `.claude/routes/<route-id>/progress.md` with state `CLASSIFIED` -> `INVESTIGATING`.
3. Run `route-implementer` through the foreground helper with mandatory Iron Law instructions (Phase 1-4: investigate root cause, pattern analysis, minimal test, targeted fix).
4. If 3 fixes fail or complexity exceeds scope, implementer reports `ESCALATE_TO_ARCHITECTURAL: <reason>`. Escalate immediately.
5. If bug is resolved with root-cause proof, update state to `REVIEWING`.
6. Update durable project `CLAUDE.md` if reusable troubleshooting knowledge was established.
7. Run `route-reviewer` through the foreground helper to verify that fix addresses root cause rather than symptoms, and passes automated/reproduction tests.
8. If Reviewer returns `VERDICT: FINDINGS`, run `route-implementer` through the foreground helper for **one targeted fix pass only**, then `route-reviewer` for final review.
9. If final review passes, proceed to **Git Completion & Push Gate** (Section 7).

### Lane D: Architectural (Complex features / refactors / multi-file changes)
1. Check Git repository and clean working tree baseline.
2. Initialize `.claude/routes/<route-id>/progress.md` with state `CLASSIFIED` -> `PLANNING`.
3. Run `route-planner` through the foreground helper. Supply request, context, and any partial edits.
4. **Mandatory Planning Gate:** Planner must brainstorm and evaluate 2-3 distinct approaches before presenting the final architecture.
5. Record plan in progress file and update state to `AWAITING_APPROVAL`.
6. Present complete plan ending with:
```text
ROUTE_STATE: AWAITING_APPROVAL
ROUTE_PLAN_ID: <short identifier>
```
7. Prompt user explicitly via `AskUserQuestion` tool to approve, request changes, or cancel implementation.
8. **HARD STOP.** Do not call `route-implementer`, edit files, or execute implementation before explicit user approval.

---

## 6. Approval Resumption & Review Bounded Loop

Approval via `AskUserQuestion` (or explicit confirmation) resumes only the latest unresolved `ROUTE_STATE: AWAITING_APPROVAL` plan in the current conversation. Without an active unresolved marker, treat responses as ordinary conversation.

Destructive or outward-facing actions (deletion, deployment, publication) require separate immediate confirmation immediately before execution even after plan approval.

### Execution Sequence
1. **Implementation Pass:** Run one foreground `run-agent.sh route-implementer` command with exact approved plan (no scope creep) and risk-based verification. Instruct implementer to prioritize immediate file modifications and verification over extended history/upstream searches. Wait for successful exit and completion banner before advancing. NEVER spawn concurrent or parallel workers.
2. **Durable Project `CLAUDE.md` Update:** Draft/apply verified reusable guidance to project `CLAUDE.md` before final review.
3. **Review 1:** Run one foreground `run-agent.sh route-reviewer` command with approved plan, diff, and test evidence (`VERDICT: PASS | FINDINGS`). Wait for successful exit and completion banner.
4. **Review 1 Pass:** If `PASS`, proceed to Git Completion.
5. **Review 1 Findings & Fix Pass:** If `FINDINGS`, run one foreground `run-agent.sh route-implementer` command for **one targeted fix pass only**.
6. **Review 2 (Final Review):** Run one foreground `run-agent.sh route-reviewer` command for final review. Strictly capped (max 1 fix pass, max 2 reviews total).
7. **Final Outcome:** If Review 2 passes, proceed to Git Completion. If it fails, record state and stop without committing.

---

## 7. Git Completion Policy, Commit Gate & Push Gate

Direct, Debug, and Architectural routes prompt user for confirmation before commit after tests and final review succeed:

1. **Delete Progress File:** Delete `.claude/routes/<route-id>/progress.md` before commit.
2. **Verify State Cleanup:** Confirm deletion leaves no route-state artifact staged or untracked.
3. **Commit Confirmation Gate:**
   - Present summary of changes (modified/created files, test results).
   - Ask for explicit user confirmation before committing changes (`git commit`).
   - If user declines commit, leave working tree clean with changes unstaged/staged as appropriate, report status, and mark route as `COMPLETED`.
4. **Focused Stage & Commit:**
   - On confirmation, set progress state to `COMMITTING`.
   - Stage ONLY route-owned implementation files, test files, documentation, and eligible project-root `CLAUDE.md` changes. Never stage unrelated baseline changes.
   - Create one focused Git commit describing the accomplishment.
   - Report the commit hash and summary to the user.
5. **Push Confirmation Gate:**
   - Ask for explicit user confirmation before running `git push`.
   - Push is an outward-facing action; never push automatically without explicit confirmation.
   - Never force-push: `git push --force` and force-with-lease are strictly prohibited.
   - If no upstream/remote exists or user declines push, report local commit and exit cleanly.
6. **Completion:** Mark route as `COMPLETED`.

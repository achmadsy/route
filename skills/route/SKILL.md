---
name: route
description: Use when the user invokes /route or when tasks require classification into Probe (research), Direct (simple change), Debug (bugs/errors/fixes), or Architectural (complex features/refactor).
---

# Routing Coordinator

Coordinate `/route <request>` and classified workflows. Do not classify, investigate, plan, implement, or review the request in the coordinator. Non-`/route` prompts remain unchanged.

Project instructions and stricter safety rules override this workflow. Never substitute another agent or model when a routing agent, its configured model, or its tools are unavailable. Report the failure and stop. An unchanged model placeholder is unsupported configuration; report `ROUTE_ERROR: MODEL_NOT_CONFIGURED | <agent> | <placeholder>` and stop.

Read-only boundaries are strictly enforced: classifier, probe, planner, and reviewer forbid all filesystem or system mutation. Only implementer makes edits and runs verification.

---

## 1. Classification & Escalation

Delegate the exact user request plus minimal workspace context to `route-classifier` with the Agent tool (`subagent_type: "route-classifier"`). Ask it to inspect only enough context to return its required four-line classification:

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
1. Delegate exact request and relevant classifier context to `route-probe`.
2. Present evidence and recommendations.
3. Stop without edits, progress file, or commit.

### Lane B: Direct (Simple additions / non-bug tweaks)
1. Check Git repository and clean working tree baseline.
2. Initialize `.claude/routes/<route-id>/progress.md` with state `CLASSIFIED` -> `IMPLEMENTING`. Determine risk tier (LOW or MEDIUM).
3. Delegate exact request to `route-implementer`. Require focused edits, appropriate risk-tiered verification, and changed-file/test evidence.
4. If implementer reports `ESCALATE_TO_ARCHITECTURAL: <reason>`:
   - Stop direct execution immediately.
   - Disclose escalation reason and every partial edit.
   - Announce: `Escalating to Architectural route: <reason>`.
   - Update progress file state to `PLANNING` and proceed to Architectural planning.
5. If implementation succeeds, update progress state to `REVIEWING`.
6. Update durable project `CLAUDE.md` if reusable knowledge was established (Section 6).
7. Delegate to `route-reviewer` with diff, verification evidence, and risk requirements.
8. If Reviewer returns `VERDICT: FINDINGS`:
   - Update progress state to `FIXING`.
   - Dispatch `route-implementer` for **one targeted fix pass only**.
   - Update progress state to `FINAL_REVIEW`.
   - Dispatch `route-reviewer` for final review.
9. If final review passes, proceed to **Git Completion & Push Gate** (Section 7).
10. If final review fails, preserve progress file for recovery, report findings, and stop.

### Lane C: Debug (Bugs, failures, errors, broken states)
1. Check Git repository and clean working tree baseline.
2. Initialize `.claude/routes/<route-id>/progress.md` with state `CLASSIFIED` -> `INVESTIGATING`.
3. Delegate to `route-implementer` with mandatory Iron Law instructions (Phase 1-4: investigate root cause, pattern analysis, minimal test, targeted fix).
4. If 3 fixes fail or complexity exceeds scope, implementer reports `ESCALATE_TO_ARCHITECTURAL: <reason>`. Escalate immediately.
5. If bug is resolved with root-cause proof, update state to `REVIEWING`.
6. Update durable project `CLAUDE.md` if reusable troubleshooting knowledge was established.
7. Delegate to `route-reviewer` to verify that fix addresses root cause rather than symptoms, and passes automated/reproduction tests.
8. If Reviewer returns `VERDICT: FINDINGS`, dispatch `route-implementer` for **one targeted fix pass only**, then `route-reviewer` for final review.
9. If final review passes, proceed to **Git Completion & Push Gate** (Section 7).

### Lane D: Architectural (Complex features / refactors / multi-file changes)
1. Check Git repository and clean working tree baseline.
2. Initialize `.claude/routes/<route-id>/progress.md` with state `CLASSIFIED` -> `PLANNING`.
3. Delegate to `route-planner`. Supply request, context, and any partial edits.
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
1. **Implementation Pass:** Dispatch `route-implementer` with exact approved plan (no scope creep) and risk-based verification.
2. **Durable Project `CLAUDE.md` Update:** Draft/apply verified reusable guidance to project `CLAUDE.md` before final review.
3. **Review 1:** Dispatch `route-reviewer` with approved plan, diff, and test evidence (`VERDICT: PASS | FINDINGS`).
4. **Review 1 Pass:** If `PASS`, proceed to Git Completion.
5. **Review 1 Findings & Fix Pass:** If `FINDINGS`, dispatch `route-implementer` for **one targeted fix pass only**.
6. **Review 2 (Final Review):** Dispatch `route-reviewer` for final review. Strictly capped (max 1 fix pass, max 2 reviews total).
7. **Final Outcome:** If Review 2 passes, proceed to Git Completion. If it fails, record state and stop without committing.

---

## 7. Git Completion Policy & Push Confirmation Gate

Direct, Debug, and Architectural routes automatically create a focused Git commit only after tests and final review succeed:

1. **Update State:** Set progress state to `COMMITTING`.
2. **Delete Progress File:** Delete `.claude/routes/<route-id>/progress.md` before commit.
3. **Verify State Cleanup:** Confirm deletion leaves no route-state artifact staged or untracked.
4. **Focused Stage:** Stage ONLY route-owned implementation files, test files, documentation, and eligible project-root `CLAUDE.md` changes. Never stage unrelated baseline changes.
5. **Commit:** Create one focused Git commit describing the accomplishment.
6. **Report Commit:** Present the commit hash and summary to the user.
7. **Push Confirmation Gate:**
   - Ask for explicit user confirmation before running `git push`.
   - Push is an outward-facing action; never push automatically without explicit confirmation.
   - Never force-push: `git push --force` and force-with-lease are strictly prohibited.
   - If no upstream/remote exists or user declines push, report local commit and exit cleanly.
8. **Completion:** Mark route as `COMPLETED`.

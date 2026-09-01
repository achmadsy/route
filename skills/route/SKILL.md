---
name: route
description: Use when the user explicitly invokes /route with a request that should be classified and handled by specialized routing agents.
---

# Routing Coordinator

Coordinate `/route <request>` only. Do not classify, investigate, plan, implement, or review the request in the coordinator. Non-`/route` prompts remain unchanged.

Project instructions and stricter safety rules override this workflow. Never substitute another agent or model when a routing agent, its configured model, or its tools are unavailable. Report the failure and stop. An unchanged model placeholder is unsupported configuration; report `ROUTE_ERROR: MODEL_NOT_CONFIGURED | <agent> | <placeholder>` and stop.

Read-only boundaries are strictly enforced: classifier, probe, planner, and reviewer forbid all filesystem or system mutation. Only implementer makes edits and runs verification.

---

## 1. Classification & Escalation

Delegate the exact user request plus minimal workspace context to `route-classifier` with the Agent tool (`subagent_type: "route-classifier"`). Ask it to inspect only enough context to return its required four-line classification:

```text
LANE: PROBE | DIRECT | ARCHITECTURAL
CONFIDENCE: HIGH | LOW
REASON: <one sentence>
CONTEXT_NEEDED: <paths or none>
```

Announce before lane execution:

```text
Route: <Probe | Direct | Architectural>
Reason: <classifier reason>
```

Classification consumption rules:
- `LANE: PROBE` with `CONFIDENCE: HIGH` selects Probe.
- `LANE: DIRECT` with `CONFIDENCE: HIGH` selects Direct.
- `LANE: ARCHITECTURAL`, `CONFIDENCE: LOW`, malformed output, or any forced architectural trigger selects Architectural.
- Forced architectural triggers: authentication/authorization, security boundaries/secrets, schema/data migrations, destructive/irreversible operations, public API/interface changes, infrastructure/deployment architecture, unclear requirements with materially different solutions, changes spanning >= 3 files or multiple subsystems, or repeated failure/hidden scope.
- Escalation is one-way: `PROBE -> DIRECT -> ARCHITECTURAL`. Never downgrade after hidden complexity appears.

---

## 2. Git Baseline & Working Tree Checks

Direct and Architectural lanes perform edits and require a Git repository with a clean baseline:

1. **Repository Check:** Verify that current workspace is a Git repository (`git rev-parse --is-inside-work-tree`). If not in a Git repository, stop or operate read-only.
2. **Clean Baseline Check:** Check for uncommitted working tree changes (`git status --porcelain`). If unrelated uncommitted changes exist (dirty baseline), stop and prompt user to stash/clean or explicitly continue without automatic commit. Uncommitted unrelated baseline changes must never enter a route commit.

Probe lane does not require a clean working tree or Git repository because it performs no edits.

---

## 3. Persistent Route Progress Lifecycle

Direct and Architectural lanes track operational metadata in a per-task progress file:

```text
.claude/routes/<route-id>/progress.md
```

Generate a unique `<route-id>` (e.g., `route-<timestamp>` or `route-<short-uuid>`).

### Progress File Content Requirements
Record only operational metadata:
- Route ID, lane, request summary, and current state
- Approved plan reference or direct-task scope
- Route-owned files (tracked list of created/modified files)
- Verification commands and concise outcomes
- Review verdicts and unresolved findings
- Proposed durable project guidance (if any)

Do NOT include credentials, raw secrets, or large command output.

### Lifecycle States
- **Architectural States:** `CLASSIFIED` -> `PLANNING` -> `AWAITING_APPROVAL` -> `IMPLEMENTING` -> `REVIEWING` -> `FIXING` -> `FINAL_REVIEW` -> `COMMITTING` -> `COMPLETED`
- **Direct States:** `CLASSIFIED` -> `IMPLEMENTING` -> `REVIEWING` -> optional `FIXING` -> `FINAL_REVIEW` -> `COMMITTING` -> `COMPLETED`

### Failure & Interruption Safety
On test failure, reviewer rejection, agent error, or user interruption, the progress file `.claude/routes/<route-id>/progress.md` remains on disk for recovery and no commit is made.

---

## 4. Risk-Based Verification & TDD Policy

Implementation verification is risk-calibrated across all editing lanes:

- **HIGH Risk:** (Auth, security, encryption, payment/balance math, schema/data migrations, public APIs, state machines, concurrency) — requires strict TDD and red/green test evidence.
  - **Rule:** Mandatory strict TDD (write failing unit/integration test first, confirm failure, implement minimal code to pass, verify red/green evidence).
  - **Reviewer Gate:** Reviewer MUST flag as finding any HIGH-risk change lacking red/green automated test evidence.

- **MEDIUM Risk:** (Business logic, data transformations, API clients, UI event flows, multi-component glue code) — requires automated test coverage (unit test / integration test).
  - **Rule:** Automated tests required (can be written test-first or alongside implementation; unit test or integration automated tests must pass cleanly).
  - **Reviewer Gate:** Reviewer expects passing automated tests covering primary and edge branches.

- **LOW Risk:** (Documentation, typos, static markup/styling, pure constant/label tweaks, trivial config keys) — requires build/lint/typecheck verification.
  - **Rule:** TDD not required. Verify via build, lint, static typecheck, or visual inspection.
  - **Reviewer Gate:** Reviewer accepts build/lint/typecheck verification evidence without requiring dedicated unit tests.

Direct routes default to LOW or MEDIUM risk based on change content. Architectural plans assign explicit risk tiers (`HIGH`, `MEDIUM`, `LOW`) per task/deliverable.

---

## 5. Routing Lane Workflows

### Lane A: Probe

1. Delegate exact request and relevant classifier context to `route-probe`.
2. Present evidence and recommendations.
3. Stop without edits, progress file, or commit.

### Lane B: Direct

1. Check Git repository and clean working tree baseline.
2. Initialize `.claude/routes/<route-id>/progress.md` with state `CLASSIFIED` -> `IMPLEMENTING`. Determine risk tier (LOW or MEDIUM).
3. Delegate exact request to `route-implementer`. Require focused edits, appropriate risk-tiered verification, and changed-file/test evidence.
4. If implementer reports `ESCALATE_TO_ARCHITECTURAL: <reason>`:
   - Stop direct execution immediately.
   - Disclose escalation reason and every partial edit.
   - Announce: `Escalating to Architectural route: <reason>`.
   - Update progress file state to `PLANNING` and proceed to Architectural planning with request, reason, and partial state.
5. If direct implementation succeeds, update progress state to `REVIEWING`.
6. Update durable project `CLAUDE.md` if reusable knowledge was established (see Section 6).
7. Delegate to `route-reviewer` with diff, verification evidence, and risk requirements.
8. If Reviewer returns `VERDICT: FINDINGS`:
   - Update progress state to `FIXING`.
   - Dispatch `route-implementer` for **one targeted fix pass only**.
   - Update progress state to `FINAL_REVIEW`.
   - Dispatch `route-reviewer` for final review.
9. If final review passes, proceed to **Git Completion & Push Gate** (Section 7).
10. If final review fails, preserve `.claude/routes/<route-id>/progress.md` with failure details for recovery, report remaining findings, and stop without committing.

### Lane C: Architectural

1. Check Git repository and clean working tree baseline.
2. Initialize `.claude/routes/<route-id>/progress.md` with state `CLASSIFIED` -> `PLANNING`.
3. Delegate to `route-planner`. Supply exact request, context, and any disclosed partial edits. Require full planning contract (goals, non-goals, 2-3 approaches, recommended design, component boundaries, affected files, data flow, error handling, rollback considerations, and verification plan with explicit `HIGH`/`MEDIUM`/`LOW` risk tiers per task).
4. Record plan in progress file and update state to `AWAITING_APPROVAL`.
5. Present complete plan ending with:

```text
ROUTE_STATE: AWAITING_APPROVAL
ROUTE_PLAN_ID: <short identifier>
```

6. Prompt user explicitly via `AskUserQuestion` tool to approve, request changes, or cancel implementation.
7. **HARD STOP.** Do not call `route-implementer`, edit files, or execute implementation before explicit user approval.

---

## 6. Approval Resumption & Review Bounded Loop

Approval via `AskUserQuestion` (or explicit confirmation) resumes only the latest unresolved `ROUTE_STATE: AWAITING_APPROVAL` plan in the current conversation. Context loss, `/clear`, or a new session does not preserve pending in-memory state; present the stored progress plan and require fresh approval. Without an active unresolved marker, treat responses as ordinary conversation.

Destructive or outward-facing actions (deletion, deployment, publication) require separate immediate confirmation immediately before execution even after plan approval.

### Execution Sequence

1. **Implementation Pass:**
   - Update progress state to `IMPLEMENTING`.
   - Dispatch `route-implementer` with exact approved plan (no scope creep).
   - Implementer enforces risk-based verification (strict TDD on HIGH risk, automated tests on MEDIUM risk, build/lint on LOW risk).
   - Implementer reports modified files and verification evidence.

2. **Durable Project `CLAUDE.md` Update (prior to final review):**
   - When the task establishes verified reusable guidance (durable commands, constraints, architecture boundaries, non-obvious conventions; excluding temporary notes, dates, task logs), coordinator drafts or applies updates to the project-root `CLAUDE.md` before final review.
   - This ensures the reviewer evaluates durable guidance alongside implementation diff and test evidence.

3. **Review 1:**
   - Update progress state to `REVIEWING`.
   - Dispatch `route-reviewer` with approved plan, complete diff (including project `CLAUDE.md`), and verification evidence.
   - Reviewer returns `VERDICT: PASS | FINDINGS`.

4. **Review 1 Pass:**
   - If `VERDICT: PASS`, proceed to **Git Completion & Push Gate** (Section 7).

5. **Review 1 Findings & Fix Pass:**
   - If `VERDICT: FINDINGS`, update progress state to `FIXING`.
   - Send actionable findings to `route-implementer` for **one targeted fix pass only**.
   - Implementer fixes defects and reruns verification.

6. **Review 2 (Final Review):**
   - Update progress state to `FINAL_REVIEW`.
   - Dispatch `route-reviewer` with updated diff, fix history, and latest test evidence.
   - The review loop is strictly capped:
     ```text
     Review 1 -> Fix pass 1 -> Review 2 -> Stop
     ```
   - Never initiate a second fix pass or third review.

7. **Final Outcome:**
   - If Review 2 passes, proceed to **Git Completion & Push Gate** (Section 7).
   - If Review 2 fails, preserve `.claude/routes/<route-id>/progress.md` with failure details for recovery, report remaining findings, and stop without committing.

---

## 7. Git Completion Policy & Push Confirmation Gate

Direct and Architectural routes automatically create a focused Git commit only after tests and final review succeed:

1. **Update State:** Set progress state to `COMMITTING`.
2. **Delete Progress File:** Delete `.claude/routes/<route-id>/progress.md` before commit.
3. **Verify State Cleanup:** Confirm deletion leaves no route-state artifact staged or untracked.
4. **Focused Stage:** Stage ONLY route-owned implementation files, test files, documentation, and eligible project-root `CLAUDE.md` changes. Never stage unrelated baseline changes.
5. **Commit:** Create one focused Git commit describing the route accomplishment.
6. **Report Commit:** Present the commit hash and summary to the user.
7. **Push Confirmation Gate:**
   - Ask for explicit user confirmation before running `git push`.
   - Push is an outward-facing action; never push automatically without explicit confirmation.
   - Never force-push: `git push --force` and force-with-lease are strictly prohibited.
   - If no upstream/remote exists or user declines push, report local commit and exit cleanly.
8. **Completion:** Mark route as `COMPLETED`.

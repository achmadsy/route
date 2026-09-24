# Claude Code `/route` Global Skill

Intelligent task routing, architecture planning, and stage-specific subagent execution for Claude Code.

## Architecture

```text
~/.claude/
├── CLAUDE.md                   # Global approval resumption rule
├── skills/
│   └── route/
│       └── SKILL.md            # Route coordinator skill
└── agents/
    ├── route-classifier.md     # Conservative 3-lane classifier
    ├── route-probe.md          # Read-only research agent
    ├── route-planner.md        # Architectural design agent
    ├── route-implementer.md    # Implementation & test engineer
    └── route-reviewer.md       # Adversarial reviewer
```

## Routing Lanes

1. **PROBE**: Read-only investigation, questions, log inspection, code search. No edits or commits.
2. **DIRECT**: Focused, reversible non-bug additions/tweaks (1-2 files). Direct implementation + strong review + commit gate + push gate.
3. **DEBUG**: Bugs, test failures, crashes, regressions, broken flows. Enforces the Iron Law of Debugging (investigate root cause first, no symptom patching, 3-fix circuit breaker).
4. **ARCHITECTURAL**: Complex changes, migrations, auth/security, public APIs, multi-file refactoring (3+ files). Evaluates 2-3 brainstormed approaches, produces comprehensive plan, and requires approval before implementation.

## Features

- **Explicit route entry only**: Ordinary main-agent work never auto-enters route. All five `route-*` agents expect route origin; the wrapper rejects prompts without `ROUTE_ORIGIN: explicit-/route`. Coordinator checks actual user invocation or active approved route before adding that marker. Use `/route <request>` or `/route continue ...` to opt in.
- **Conservative classification**: Low confidence or security/migration/API triggers force `ARCHITECTURAL`. All bug fixes force `DEBUG`.
- **The Iron Law of Debugging**: Mandatory 4-phase debugging (root cause investigation, pattern analysis, hypothesis testing, targeted fix & verify) with 3-fix circuit breaker.
- **Mandatory brainstorming gate**: Architectural plans evaluate 2-3 distinct approaches with explicit trade-offs.
- **Persistent progress tracking**: `.claude/routes/<route-id>/progress.md` tracks state for Direct, Debug, and Architectural routes; deleted before commit on success; preserved on failure for recovery.
- **Risk-based TDD verification**:
  - `HIGH`: Strict TDD (failing test first, make pass, red/green evidence required).
  - `MEDIUM`: Automated tests required.
  - `LOW`: Build, lint, or typecheck verification.
- **Strict single-agent enforcement**: Run exactly one route agent in foreground; never dispatch another before its exit and validated completion banner.
- **Heartbeat and stuck-run bound**: Foreground wrapper reports progress every `ROUTE_HEARTBEAT_SECONDS` (default 60) and stops an agent after `ROUTE_AGENT_MAX_SECONDS` (default 540). No second monitoring agent or heartbeat cron starts.
- **Agent-owned model selection**: Foreground `claude -p --agent` dispatch omits `--model`; each `route-*` agent's `model:` frontmatter remains sole model authority, including custom gateway aliases.
- **Durable project `CLAUDE.md` updates**: Reusable lessons drafted and reviewed together before final review.
- **agentmemory integration**: When the `agentmemory` MCP server is available, lanes recall prior decisions first (`memory_smart_search` / `memory_recall`) and save settled decisions/root causes at the moment they resolve (`memory_save`); corrections become lessons (`memory_lesson_save`). Missing memory tools never block a route.
- **Git workflow**: Clean baseline check, explicit confirmation gate before `git commit`, explicit confirmation gate before `git push`, force-push prohibited.
- **Bounded review loop**: Capped at `Review 1 -> Fix pass 1 -> Review 2 -> Stop`.

## Installation on a New Machine

1. Clone or copy this repository:
```bash
git clone git@github.com:achmadsy/route.git
cd route
```

2. Copy files to your global `~/.claude` directory:
```bash
mkdir -p ~/.claude/skills/route ~/.claude/agents
cp -r skills/route/* ~/.claude/skills/route/
cp agents/route-*.md ~/.claude/agents/
```

3. Configure global approval resumption in `~/.claude/CLAUDE.md`:
```bash
# If ~/.claude/CLAUDE.md does not exist:
cp CLAUDE.md ~/.claude/CLAUDE.md

# If ~/.claude/CLAUDE.md already exists, append the contents of CLAUDE.md to it.
```

4. Configure models only in `~/.claude/agents/route-*.md`:
Open each file in `~/.claude/agents/` and set its `model:` frontmatter to a model supported by your Claude Code gateway. The provided files use custom gateway model names (`classifier-agent`, `probe-agent`, etc.); configure them for your provider before use. Route coordinator launches `claude -p --agent` without `--model`, preserving each agent's model choice. Python 3 is required for the foreground heartbeat wrapper. Foreground CLI route phases create separate Claude sessions and inherit local CLI settings; they are not in-process `Agent` tool calls.

5. Optional — agentmemory (shared long-term memory):
Install the [agentmemory](https://github.com/rohitg00/agentmemory) plugin/MCP so routes can recall prior decisions and save settled ones. Clients only need:
```bash
export AGENTMEMORY_URL=http://<server-host>:3111
export AGENTMEMORY_SECRET=<server-secret>
```
Server-side flags (graph extraction, consolidation, auto-compress) stay on the memory server, not on route clients.

## Usage

In any project repository, run:

```text
/route <your request>
/route continue <path-to-plan-or-progress.md>
```

`/route continue` resumes validated partial development without re-running architecture selection or planning. It preserves approved scope and requires fresh execution confirmation for prior-session Markdown. Generic or invalid Markdown stops safely.

For new requests, optional Jev classification uses native System One:

```text
ANTHROPIC_BASE_URL=http://127.0.0.1:20128/v1
ANTHROPIC_AUTH_TOKEN=...
skills/route/classify-jev.sh "add feature request"
```

The adapter posts to `${ANTHROPIC_BASE_URL%/}/systemone` with model `oc/jev-1.13-free`, `state`, and `questions` using `type: "noul"`. Jev failure (including ambiguous scores) falls back to `bash skills/route/run-agent.sh route-classifier` using the agent file's `classifier-agent` model. Jev must not receive chat-completions JSON. Example: `printf 'ROUTE_ORIGIN: explicit-/route\n%s' '1+2=?' | bash skills/route/run-agent.sh route-classifier`. The wrapper validates completion banners and prints periodic progress on stderr without starting another agent.

Examples:
- `/route find where rate limiting middleware is applied` -> **PROBE**
- `/route fix typo in README` -> **DIRECT**
- `/route add OAuth2 Google authentication` -> **ARCHITECTURAL** (requires `yes` before code edits)

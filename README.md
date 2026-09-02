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

- **Conservative classification**: Low confidence or security/migration/API triggers force `ARCHITECTURAL`. All bug fixes force `DEBUG`.
- **The Iron Law of Debugging**: Mandatory 4-phase debugging (root cause investigation, pattern analysis, hypothesis testing, targeted fix & verify) with 3-fix circuit breaker.
- **Mandatory brainstorming gate**: Architectural plans evaluate 2-3 distinct approaches with explicit trade-offs.
- **Persistent progress tracking**: `.claude/routes/<route-id>/progress.md` tracks state for Direct, Debug, and Architectural routes; deleted before commit on success; preserved on failure for recovery.
- **Risk-based TDD verification**:
  - `HIGH`: Strict TDD (failing test first, make pass, red/green evidence required).
  - `MEDIUM`: Automated tests required.
  - `LOW`: Build, lint, or typecheck verification.
- **Durable project `CLAUDE.md` updates**: Reusable lessons drafted and reviewed together before final review.
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

4. Configure model aliases in `~/.claude/agents/route-*.md`:
Open each file in `~/.claude/agents/` and adjust the `model:` field to your desired model ID:
- `route-classifier.md`: `haiku` (or fast model)
- `route-probe.md`: `sonnet`
- `route-planner.md`: `fable` / `opus` (strongest model)
- `route-implementer.md`: `sonnet`
- `route-reviewer.md`: `fable` / `opus` (strongest model)

## Usage

In any project repository, run:

```text
/route <your request>
```

Examples:
- `/route find where rate limiting middleware is applied` -> **PROBE**
- `/route fix typo in README` -> **DIRECT**
- `/route add OAuth2 Google authentication` -> **ARCHITECTURAL** (requires `yes` before code edits)

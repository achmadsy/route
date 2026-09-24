#!/usr/bin/env python3
"""Run one configured route agent; emit heartbeat and validate its completion."""

import json
import os
import selectors
import signal
import subprocess
import sys
import time

AGENTS = {
    "route-classifier": "CLASSIFIER_STATUS",
    "route-probe": "PROBE_STATUS",
    "route-planner": "PLANNER_STATUS",
    "route-implementer": "IMPLEMENTER_STATUS",
    "route-reviewer": "REVIEWER_STATUS",
}
LANES = {"PROBE", "DIRECT", "DEBUG", "ARCHITECTURAL"}
READ_ONLY_TOOLS = ",".join((
    "Read", "Glob", "Grep", "WebFetch", "WebSearch",
    "mcp__codebase-memory-mcp__list_projects",
    "mcp__codebase-memory-mcp__index_status",
    "mcp__codebase-memory-mcp__search_graph",
    "mcp__codebase-memory-mcp__trace_path",
    "mcp__codebase-memory-mcp__get_code_snippet",
    "mcp__codebase-memory-mcp__get_architecture",
    "mcp__codebase-memory-mcp__search_code",
    "mcp__codebase-memory-mcp__query_graph",
    "mcp__codebase-memory-mcp__get_graph_schema",
    "mcp__codebase-memory-mcp__detect_changes",
    "mcp__codebase-memory-mcp__check_index_coverage",
    "mcp__agentmemory__memory_smart_search",
    "mcp__agentmemory__memory_recall",
    "mcp__agentmemory__memory_lesson_recall",
    "mcp__agentmemory__memory_file_history",
))


def fail(reason):
    print(f"route agent: {reason}", file=sys.stderr)
    return 3


def valid_result(agent, result):
    lines = set(result.splitlines())
    marker = AGENTS[agent]
    if f"{marker}: COMPLETE" not in lines:
        return False
    if agent == "route-classifier":
        return (
            any(f"LANE: {lane}" in lines for lane in LANES)
            and any(line in lines for line in ("CONFIDENCE: HIGH", "CONFIDENCE: LOW"))
            and any(line.startswith("REASON: ") for line in lines)
            and any(line.startswith("CONTEXT_NEEDED: ") for line in lines)
        )
    if agent == "route-planner":
        return "ROUTE_STATE: AWAITING_APPROVAL" in lines and any(
            line.startswith("ROUTE_PLAN_ID: ") for line in lines
        )
    if agent == "route-implementer":
        return any(line.startswith("FILES: ") for line in lines) and any(
            line.startswith("TESTS: ") for line in lines
        )
    if agent == "route-reviewer":
        return "VERDICT: PASS" in lines or "VERDICT: FINDINGS" in lines
    return True


def stop_process(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in AGENTS:
        return fail("unknown agent")
    agent = sys.argv[1]
    prompt = sys.stdin.read()
    if not prompt.startswith("ROUTE_ORIGIN: explicit-/route\n") or not prompt.partition("\n")[2].strip():
        return fail("missing explicit route origin and request")

    try:
        heartbeat = max(1, int(os.getenv("ROUTE_HEARTBEAT_SECONDS", "60")))
        deadline = max(1, int(os.getenv("ROUTE_AGENT_MAX_SECONDS", "540")))
    except ValueError:
        return fail("invalid heartbeat or deadline")

    command = [
        "claude", "-p", "--agent", agent, "--output-format", "stream-json",
        "--verbose", "--permission-prompts", "none",
    ]
    if agent == "route-implementer":
        command.extend(["--permission-mode", "acceptEdits", "--disallowedTools", "Agent,Workflow"])
    else:
        command.extend(["--permission-mode", "plan", "--tools", READ_ONLY_TOOLS])

    try:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, bufsize=1, start_new_session=True,
        )
    except OSError:
        return fail(f"could not start {agent}")

    def interrupt(_signal, _frame):
        raise KeyboardInterrupt

    previous_term = signal.signal(signal.SIGTERM, interrupt)
    try:
        process.stdin.write(prompt)
        process.stdin.close()
    except (BrokenPipeError, KeyboardInterrupt):
        stop_process(process)
        signal.signal(signal.SIGTERM, previous_term)
        return fail(f"{agent} stopped before prompt delivery")

    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    started = time.monotonic()
    last_event = started
    next_heartbeat = started + heartbeat
    result = None
    try:
        while True:
            now = time.monotonic()
            if now - started >= deadline:
                stop_process(process)
                return fail(f"{agent} exceeded {deadline}s deadline")
            if now >= next_heartbeat:
                print(
                    f"route agent: {agent} active {int(now - started)}s; "
                    f"last event {int(now - last_event)}s ago",
                    file=sys.stderr, flush=True,
                )
                next_heartbeat = now + heartbeat
            events = selector.select(timeout=max(0, min(1, next_heartbeat - now, deadline - (now - started))))
            for _, _ in events:
                line = process.stdout.readline()
                if not line:
                    selector.unregister(process.stdout)
                    continue
                last_event = time.monotonic()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "result":
                    result = event
            if process.poll() is not None and not selector.get_map():
                break
    except KeyboardInterrupt:
        stop_process(process)
        return fail(f"{agent} interrupted")
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        selector.close()
        process.stdout.close()

    if process.returncode != 0 or not result or result.get("is_error") or result.get("subtype") != "success":
        return fail(f"{agent} failed (exit {process.returncode})")
    text = result.get("result")
    if not isinstance(text, str) or not valid_result(agent, text):
        return fail(f"{agent} returned invalid completion banner")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

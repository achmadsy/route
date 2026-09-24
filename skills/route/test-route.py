#!/usr/bin/env python3
"""Fixture-based checks for route classification and foreground agent dispatch."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

HERE = Path(__file__).resolve().parent


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.env = dict(os.environ, PATH=f"{self.directory}:{os.environ['PATH']}")

    def executable(self, name, body):
        path = self.directory / name
        path.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body))
        path.chmod(0o755)

    def run_jev(self, reply):
        self.executable("curl", f"print({json.dumps(reply)!r})\n")
        self.env.update(ANTHROPIC_BASE_URL="http://127.0.0.1:1/v1", ANTHROPIC_AUTH_TOKEN="fixture")
        return subprocess.run(
            ["bash", str(HERE / "classify-jev.sh"), "1+2=?"],
            env=self.env, text=True, capture_output=True, timeout=10,
        )

    def test_jev_clear_result(self):
        answer = {lane: {"noul": score} for lane, score in
                  {"probe": 0.92, "direct": 0.01, "debug": 0.01, "architectural": 0.02}.items()}
        output = self.run_jev({"answers": answer})
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertIn("LANE: PROBE", output.stdout)

    def test_jev_ambiguous_and_invalid_fall_back(self):
        for reply in (
            {"answers": {lane: {"noul": score} for lane, score in
                         {"probe": 0.37, "direct": 0.27, "debug": 0.02, "architectural": 0.03}.items()}},
            {"answers": {}},
        ):
            with self.subTest(reply=reply):
                output = self.run_jev(reply)
                self.assertNotEqual(output.returncode, 0)
                self.assertFalse(output.stdout)

    def test_jev_missing_configuration(self):
        env = dict(self.env)
        env.pop("ANTHROPIC_BASE_URL", None)
        output = subprocess.run(
            ["bash", str(HERE / "classify-jev.sh"), "1+2=?"],
            env=env, text=True, capture_output=True, timeout=10,
        )
        self.assertNotEqual(output.returncode, 0)

    def run_agent(self, mock, env=None):
        self.executable("claude", mock)
        return subprocess.run(
            ["bash", str(HERE / "run-agent.sh"), "route-classifier"],
            input="ROUTE_ORIGIN: explicit-/route\n1+2=?", env={**self.env, **(env or {})},
            text=True, capture_output=True, timeout=10,
        )

    def test_classifier_fallback_keeps_agent_model(self):
        result = "CLASSIFIER_STATUS: COMPLETE\nLANE: PROBE\nCONFIDENCE: HIGH\nREASON: math question\nCONTEXT_NEEDED: none"
        mock = f"""
import json, sys
assert sys.argv[1:3] == ['-p', '--agent']
assert sys.argv[3] == 'route-classifier'
assert sys.stdin.read() == 'ROUTE_ORIGIN: explicit-/route\\n1+2=?'
assert '--model' not in sys.argv
assert 'plan' in sys.argv
assert '--tools' in sys.argv
assert 'Bash' not in sys.argv[-1]
assert 'Edit' not in sys.argv[-1]
print(json.dumps({{'type': 'result', 'subtype': 'success', 'is_error': False, 'result': {result!r}}}))
"""
        output = self.run_agent(mock)
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertIn("LANE: PROBE", output.stdout)

    def test_agent_rejects_non_route_prompt_before_launch(self):
        self.executable("claude", "raise AssertionError('must not launch')\n")
        output = subprocess.run(
            ["bash", str(HERE / "run-agent.sh"), "route-classifier"],
            input="ordinary work", env=self.env,
            text=True, capture_output=True, timeout=10,
        )
        self.assertNotEqual(output.returncode, 0)
        self.assertIn("missing explicit route origin", output.stderr)

    def test_agent_rejects_missing_banner(self):
        mock = "import json\nprint(json.dumps({'type':'result','subtype':'success','is_error':False,'result':'prose only'}))\n"
        output = self.run_agent(mock)
        self.assertNotEqual(output.returncode, 0)
        self.assertFalse(output.stdout)

    def test_agent_heartbeat_and_deadline(self):
        output = self.run_agent("import time\ntime.sleep(4)\n", {
            "ROUTE_HEARTBEAT_SECONDS": "1", "ROUTE_AGENT_MAX_SECONDS": "2",
        })
        self.assertNotEqual(output.returncode, 0)
        self.assertIn("active", output.stderr)
        self.assertIn("deadline", output.stderr)


if __name__ == "__main__":
    unittest.main()

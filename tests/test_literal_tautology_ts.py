"""Regression test: expect(true).toBe(true) must be proven, not advisory.

The self-compare-call check (advisory: "equal by construction unless
nondeterministic") ran before the constant-assert check and also matched
literal-vs-literal comparisons — but identical literals cannot be
nondeterministic, so the canonical tautology the README leads with was
only ever advisory and --fix never removed it.

Stdlib only — run with:  python3 -m unittest discover tests
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "skills", "captain-obvious", "scripts")
CLI = os.path.join(SCRIPTS, "captain_obvious_ts.mjs")

NODE = shutil.which("node")


def _ts_resolvable() -> bool:
    if not NODE:
        return False
    probe = subprocess.run(
        [NODE, "-e", "import('typescript').then(()=>process.exit(0),()=>process.exit(1))"],
        cwd=SCRIPTS, capture_output=True)
    return probe.returncode == 0


TEST_SRC = '''\
test("truth", () => {
  expect(true).toBe(true);
});
test("self compare call", () => {
  expect(f(1)).toEqual(f(1));
});
'''


@unittest.skipUnless(_ts_resolvable(), "node + typescript not available")
class LiteralTautologyIsProven(unittest.TestCase):
    def test_literal_vs_literal_is_constant_assert_proven(self):
        d = tempfile.mkdtemp(prefix="capobv-lit-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with open(os.path.join(d, "lit.test.ts"), "w", encoding="utf-8") as fh:
            fh.write(TEST_SRC)
        out = os.path.join(d, "report.json")
        subprocess.run([NODE, CLI, "--project", d, "--json", out],
                       capture_output=True, text=True, check=True)
        with open(out, encoding="utf-8") as fh:
            findings = json.load(fh)["findings"]
        by_test = {f["test"]: f for f in findings}
        self.assertEqual(by_test["truth"]["category"], "constant-assert")
        self.assertEqual(by_test["truth"]["level"], "proven")
        # calls can be nondeterministic — must stay advisory
        self.assertEqual(by_test["self compare call"]["category"], "self-compare-call")
        self.assertEqual(by_test["self compare call"]["level"], "advisory")


if __name__ == "__main__":
    unittest.main()

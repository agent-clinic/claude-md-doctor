"""End-to-end tests for the claude-md-doctor scripts (stdlib only).

Run:  python3 -m unittest discover -s tests -v
Each test builds a toy repo in a temp dir and drives the real CLIs.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "claude-md-doctor", "scripts")
sys.path.insert(0, SCRIPTS)
import _common  # noqa: E402


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, "%s failed:\n%s\n%s" % (script, r.stdout, r.stderr)
    return r.stdout


def jload(work, name):
    with open(os.path.join(work, name)) as f:
        return json.load(f)


class TestCommon(unittest.TestCase):
    def test_html_comments_stripped_outside_fences_only(self):
        text = "keep\n<!-- gone -->\n```\n<!-- kept in fence -->\n```\n"
        clean, removed = _common.strip_html_comments(text)
        self.assertEqual(removed, 1)
        self.assertIn("kept in fence", clean)
        self.assertNotIn("gone", clean)

    def test_frontmatter_paths_list(self):
        meta, body = _common.parse_frontmatter(
            "---\npaths:\n  - \"src/**/*.ts\"\n  - lib/*.ts\n---\nBody\n")
        self.assertEqual(meta["paths"], ["src/**/*.ts", "lib/*.ts"])
        self.assertEqual(body.strip(), "Body")


class ToyRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "repo")
        self.work = os.path.join(self.tmp.name, "work")
        os.makedirs(os.path.join(self.repo, "docs"))
        os.makedirs(os.path.join(self.repo, ".claude", "rules"))
        self._w("docs/extra.md", "# extra\nRun `pnpm nope` and `pnpm build`.\n")
        self._w("exists.md", "hi\n")
        self._w("package.json", json.dumps({"scripts": {"build": "true"}}))
        self._w(".claude/rules/scoped.md",
                "---\npaths:\n  - \"src/**/*.zz\"\n---\nNever do the thing.\n")
        self._w("CLAUDE.md", "\n".join([
            "This file provides guidance to Claude Code (claude.ai/code).",
            "# Toy", "@docs/extra.md", "@docs/missing.md",
            "See `@literal` (not an import) and `exists.md` and `missing.md`.",
            "NEVER touch `/Users/someoneelse/secret/thing.md`.",
            "ALWAYS pass. IMPORTANT: `/**` is punctuation. Updated 2026-01-02.", ""]))

    def tearDown(self):
        self.tmp.cleanup()

    def _w(self, rel, content):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)


class TestIntake(ToyRepo):
    def test_discovery_imports_and_rules(self):
        run("intake.py", "--repo", self.repo, "--work", self.work)
        intake = jload(self.work, "intake.json")
        scopes = {f["scope"] for f in intake["files"]}
        self.assertIn("project", scopes)
        self.assertIn("rules", scopes)
        edges = {e["ref"]: e["exists"] for e in intake["import_edges"]}
        self.assertTrue(edges["docs/extra.md"])
        self.assertFalse(edges["docs/missing.md"])
        self.assertNotIn("literal", "".join(edges))  # backticked = literal
        rules = [f for f in intake["files"] if f["scope"] == "rules"][0]
        self.assertEqual(rules["rules_paths"], ["src/**/*.zz"])
        self.assertFalse(rules["loaded_at_launch"])  # path-scoped -> on demand

    def test_pointer_detection_import_style(self):
        self._w("AGENTS.md", "# real content\nRun `pnpm build`.\n")
        self._w("CLAUDE.md", "@AGENTS.md\n")
        run("intake.py", "--repo", self.repo, "--work", self.work)
        proj = [f for f in jload(self.work, "intake.json")["files"]
                if f["scope"] == "project"][0]
        self.assertTrue(proj["is_pointer"])
        self.assertEqual(proj["pointer_style"], "import")

    def test_pointer_detection_bare_text_is_flagged_style(self):
        self._w("AGENTS.md", "# real content\n")
        self._w("CLAUDE.md", "AGENTS.md\n")  # no @ — target never loads
        run("intake.py", "--repo", self.repo, "--work", self.work)
        proj = [f for f in jload(self.work, "intake.json")["files"]
                if f["scope"] == "project"][0]
        self.assertTrue(proj["is_pointer"])
        self.assertEqual(proj["pointer_style"], "bare-text")


class TestVitalsRefcheck(ToyRepo):
    def setUp(self):
        super().setUp()
        run("intake.py", "--repo", self.repo, "--work", self.work)
        run("vitals.py", "--work", self.work)
        run("refcheck.py", "--work", self.work)

    def test_vitals_markers(self):
        m = jload(self.work, "vitals.json")["per_file"][
            os.path.realpath(os.path.join(self.repo, "CLAUDE.md"))]
        self.assertTrue(m["init_boilerplate"])
        self.assertGreater(m["emphasis_lines"], 0)
        self.assertGreater(m["dated_lines"], 0)

    def test_refcheck_statuses(self):
        rc = jload(self.work, "refcheck.json")
        by_ref = {r["ref"]: r["status"] for r in rc["references"]}
        self.assertEqual(by_ref["exists.md"], "ok")
        self.assertEqual(by_ref["missing.md"], "missing")
        self.assertEqual(by_ref["/Users/someoneelse/secret/thing.md"],
                         "machine_specific")
        self.assertNotIn("/**", by_ref)  # pure punctuation never checked
        cmds = {c["command"]: c["status"] for c in rc["commands"]}
        self.assertEqual(cmds["pnpm build"], "ok")
        self.assertEqual(cmds["pnpm nope"], "missing")
        scope = rc["rule_scopes"][0]
        self.assertEqual(scope["status"], "dead_scope")  # *.zz matches nothing


class TestBacktest(ToyRepo):
    def test_engine_violation_compliance_ordering_repo_only(self):
        run("intake.py", "--repo", self.repo, "--work", self.work)
        sdir = os.path.join(self.work, "sessions")
        os.makedirs(sdir)
        events = [
            {"t": "tool", "name": "Edit", "turn": 2, "ts": "2026-08-01T00:00:00Z",
             "file_path": os.path.join(os.path.realpath(self.repo), "src", "a.ts"),
             "new": "const x = fetch('/api')"},
            {"t": "tool", "name": "Edit", "turn": 3, "ts": "2026-08-01T00:01:00Z",
             "file_path": "/somewhere/else/outside.ts", "new": "fetch('/x')"},
            {"t": "tool", "name": "Bash", "turn": 4, "ts": "2026-08-01T00:02:00Z",
             "command": "pnpm build"},
        ]
        with open(os.path.join(sdir, "s1.json"), "w") as f:
            json.dump(events, f)
        with open(os.path.join(self.work, "sessions_index.json"), "w") as f:
            json.dump({"sessions": [{"id": "s1", "events": 3, "tools": 3,
                                     "last_ts": "2026-08-01T00:02:00Z"}]}, f)
        with open(os.path.join(self.work, "rulebook.json"), "w") as f:
            json.dump({"rules": [
                {"id": "V1", "text": "no fetch",
                 "scope": {"events": ["edit", "write"], "repo_only": True},
                 "matchers": {"violation": "\\bfetch\\s*\\("}},
                {"id": "O1", "text": "verify before finish",
                 "scope": {"events": ["edit", "write"], "repo_only": True},
                 "ordering": {"require": "pnpm verify", "desc": "verify",
                              "min_mutations": 1}},
            ]}, f)
        run("backtest.py", "--work", self.work)
        bt = jload(self.work, "backtest.json")["per_rule"]
        self.assertEqual(bt["V1"]["violations"], 1)   # outside-repo edit excluded
        self.assertEqual(bt["O1"]["violations"], 1)   # build ran, verify didn't
        self.assertEqual(bt["V1"]["violations_by_depth"]["early"], 1)
        viz = bt["O1"]["samples"]["violations"][0]["viz"]
        self.assertEqual(viz["edits"], 1)
        self.assertEqual(viz["after_cmds"], [["pnpm", 1]])
        self.assertTrue(any(s["after"] for s in viz["segments"]))


class TestReport(ToyRepo):
    def test_report_renders_and_discloses_incomplete(self):
        run("intake.py", "--repo", self.repo, "--work", self.work)
        run("vitals.py", "--work", self.work)
        run("refcheck.py", "--work", self.work)
        out = os.path.join(self.tmp.name, "r.html")
        run("report.py", "--work", self.work, "--out", out)  # no diagnosis.json
        with open(out) as f:
            html = f.read()
        self.assertNotIn("{{", html)
        self.assertIn("Incomplete exam", html)       # diagnosis stage missing
        self.assertIn("machine specific", html)


if __name__ == "__main__":
    unittest.main()

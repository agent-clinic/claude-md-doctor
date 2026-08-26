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

    def test_orphan_agents_md_detected(self):
        os.remove(os.path.join(self.repo, "CLAUDE.md"))
        self._w("AGENTS.md", "# rules for all agents\nRun `pnpm build`.\n")
        run("intake.py", "--repo", self.repo, "--work", self.work)
        intake = jload(self.work, "intake.json")
        orphans = [f for f in intake["files"] if f["scope"] == "orphan-agents"]
        self.assertEqual(len(orphans), 1)
        self.assertTrue(orphans[0]["orphaned"])
        self.assertFalse(orphans[0]["loaded_at_launch"])

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
        self.assertIn("cause", bt["V1"]["samples"]["violations"][0])
        self.assertIn("arming", bt["V1"])

    def test_cause_triage_and_compile(self):
        run("intake.py", "--repo", self.repo, "--work", self.work)
        sdir = os.path.join(self.work, "sessions")
        os.makedirs(sdir)
        repo = os.path.realpath(self.repo)
        events = [
            # early violation, fresh context -> defiance
            {"t": "tool", "name": "Edit", "turn": 2, "off": 1000,
             "file_path": os.path.join(repo, "a.ts"), "new": "evil()"},
            # the agent echoes the rule, then violates again -> defiance-proven
            {"t": "assistant", "turn": 3, "off": 2000,
             "text": "I must never call evil() per the rules."},
            {"t": "tool", "name": "Edit", "turn": 4, "off": 3000,
             "file_path": os.path.join(repo, "b.ts"), "new": "evil()"},
            # compaction, then a nested-origin rule violation -> absence-risk
            {"t": "compact", "turn": 5, "off": 4000},
            {"t": "tool", "name": "Edit", "turn": 6, "off": 5000,
             "file_path": os.path.join(repo, "c.ts"), "new": "spooky()"},
            # very late turn -> dilution
            {"t": "tool", "name": "Edit", "turn": 20, "off": 6000,
             "file_path": os.path.join(repo, "d.ts"), "new": "chaotic()"},
        ]
        with open(os.path.join(sdir, "s1.json"), "w") as f:
            json.dump(events, f)
        with open(os.path.join(self.work, "sessions_index.json"), "w") as f:
            json.dump({"sessions": [{"id": "s1", "events": len(events),
                                     "tools": 4,
                                     "last_ts": "2026-08-01T00:02:00Z"}]}, f)
        with open(os.path.join(self.work, "rulebook.json"), "w") as f:
            json.dump({"rules": [
                {"id": "E1", "text": "never call evil", "origin": "root",
                 "scope": {"events": ["edit", "write"]},
                 "matchers": {"violation": "evil\\("},
                 "enforcement": {"class": "hook", "current_layer": "prose",
                                 "echo_regex": "never call evil"}},
                {"id": "A1", "text": "never call spooky", "origin": "rules",
                 "scope": {"events": ["edit", "write"]},
                 "matchers": {"violation": "spooky\\("},
                 "enforcement": {"class": "hook", "current_layer": "prose"}},
                {"id": "D1", "text": "never call chaotic", "origin": "root",
                 "scope": {"events": ["edit", "write"]},
                 "matchers": {"violation": "chaotic\\("},
                 "enforcement": {"class": "hook", "current_layer": "prose"}},
                {"id": "L1", "text": "already a law", "origin": "root",
                 "scope": {"events": ["edit", "write"]},
                 "matchers": {"violation": "nope\\("},
                 "enforcement": {"class": "linter", "current_layer": "test"}},
            ]}, f)
        run("backtest.py", "--work", self.work)
        bt = jload(self.work, "backtest.json")["per_rule"]
        self.assertEqual(bt["E1"]["causes"].get("defiance"), 1)
        self.assertEqual(bt["E1"]["causes"].get("defiance-proven"), 1)
        self.assertIn("BLOCK-ready", bt["E1"]["arming"])
        self.assertEqual(bt["A1"]["causes"], {"absence-risk": 1})
        self.assertIn("re-inject", bt["A1"]["arming"])
        self.assertEqual(bt["D1"]["causes"], {"dilution": 1})
        self.assertIn("soft first", bt["D1"]["arming"])
        self.assertIn("already enforced", bt["L1"]["arming"])
        run("compile.py", "--work", self.work)
        enf_dir = os.path.join(self.work, "enforcement")
        cfg = jload(enf_dir, "rules-guard.json")
        ids = {r["id"]: r for r in cfg["rules"]}
        self.assertIn("E1", ids)
        self.assertEqual(ids["E1"]["mode"], "block")   # defiance-proven -> block
        self.assertEqual(ids["D1"]["mode"], "warn")
        self.assertNotIn("L1", ids)                     # already enforced -> no guard
        with open(os.path.join(enf_dir, "PROPOSALS.md")) as f:
            proposals = f.read()
        self.assertIn("REVIEW BEFORE ARMING", proposals)
        self.assertIn("BLOCK-ready", proposals)

    def test_share_card_is_aggregate_only(self):
        run("intake.py", "--repo", self.repo, "--work", self.work)
        run("vitals.py", "--work", self.work)
        with open(os.path.join(self.work, "rulebook.json"), "w") as f:
            json.dump({"rules": [
                {"id": "S1", "text": "SECRET-RULE-TEXT never do the thing",
                 "source": {"file": "CLAUDE.md", "line": 4},
                 "scope": {"events": ["edit"]},
                 "matchers": {"violation": "zzz"},
                 "enforcement": {"class": "hook", "current_layer": "prose"}},
            ]}, f)
        with open(os.path.join(self.work, "diagnosis.json"), "w") as f:
            json.dump({"grade": "B",
                       "rule_verdicts": {"S1": {"verdict": "ignored",
                                                "note": "SECRET-NOTE"}},
                       "diagnoses": [{"severity": "critical", "state": "stale",
                                      "title": "SECRET-TITLE",
                                      "detail": "SECRET-DETAIL"}]}, f)
        run("card.py", "--work", self.work)
        parent = os.path.dirname(self.work)
        with open(os.path.join(parent, "card.svg")) as f:
            card = f.read()
        with open(os.path.join(parent, "claude-md-health.svg")) as f:
            badge = f.read()
        # privacy: aggregates only — nothing from the repo's content leaks
        for leak in ("SECRET", self.repo, "/Users/", "CLAUDE.md:", "exists.md"):
            self.assertNotIn(leak, card)
        self.assertIn("The loudest rule was the broken one.", card)  # fallback note
        self.assertIn("1 could be laws", card)
        self.assertIn("grade B", badge)
        # --anonymous omits even the repo basename
        run("card.py", "--work", self.work, "--anonymous")
        with open(os.path.join(parent, "card.svg")) as f:
            anon = f.read()
        self.assertNotIn(os.path.basename(self.repo), anon)


class TestVersionSync(unittest.TestCase):
    def test_report_version_matches_plugin_manifest(self):
        # The report footer stamps report.VERSION; the marketplace ships
        # plugin.json's version. They drifted once (0.3.5 vs 0.4.3) — keep
        # them locked. Skip outside the repo (bare installs have no manifest).
        manifest = os.path.join(ROOT, ".claude-plugin", "plugin.json")
        if not os.path.isfile(manifest):
            self.skipTest("no plugin manifest (bare install)")
        import report
        with open(manifest) as f:
            plugin_version = json.load(f)["version"]
        self.assertEqual(report.VERSION, plugin_version)


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

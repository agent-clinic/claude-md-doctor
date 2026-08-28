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


class TestSessionsCondense(unittest.TestCase):
    def test_meta_sidechain_skipped_and_denials_carried(self):
        import sessions as sessions_mod
        tmp = tempfile.TemporaryDirectory()
        path = os.path.join(tmp.name, "t.jsonl")
        recs = [
            {"type": "user", "isMeta": True, "timestamp": "2026-08-01T00:00:00Z",
             "message": {"content": [{"type": "text",
                                      "text": "Base directory for this skill: …"}]}},
            {"type": "user", "isSidechain": True,
             "message": {"content": "orchestrator prompt"}},
            {"type": "user", "origin": {"kind": "human"},
             "timestamp": "2026-08-01T00:01:00Z",
             "message": {"content": "no, use pnpm"}},
            {"type": "assistant", "timestamp": "2026-08-01T00:01:30Z",
             "message": {"content": [{"type": "tool_use",
                                      "id": "toolu_ABCDEF12345678",
                                      "name": "Bash",
                                      "input": {"command": "git push"}}]}},
            {"type": "user", "toolDenialKind": "user-rejected",
             "timestamp": "2026-08-01T00:02:00Z",
             "message": {"content": [{"type": "tool_result", "is_error": True,
                                      "tool_use_id": "toolu_ABCDEF12345678",
                                      "content": "The user doesn't want to proceed"}]}},
        ]
        with open(path, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        events, meta = sessions_mod.condense_file(path)
        texts = [e.get("text", "") for e in events]
        self.assertNotIn("Base directory for this skill: …", texts)
        self.assertNotIn("orchestrator prompt", texts)
        human = [e for e in events if e["t"] == "user"]
        self.assertEqual(len(human), 1)
        self.assertEqual(human[0]["src"], "human")
        tools = [e for e in events if e["t"] == "tool"]
        self.assertEqual(tools[0]["id"], "12345678")       # short id carried
        errs = [e for e in events if e["t"] == "tool_error"]
        self.assertEqual(errs[0]["denial"], "user-rejected")
        self.assertEqual(errs[0]["for_id"], "12345678")    # error ↔ call tie
        tmp.cleanup()


class TestMine(ToyRepo):
    def _sessions(self):
        sdir = os.path.join(self.work, "sessions")
        os.makedirs(sdir, exist_ok=True)
        opener = ("this repo is the acme monorepo, app lives in apps/web and "
                  "the api in services/api")
        s1 = [
            {"t": "user", "turn": 1, "off": 0, "ts": "2026-08-20T00:00:00Z",
             "text": opener},
            {"t": "tool", "name": "Bash", "turn": 1, "off": 100,
             "command": "cat package.json"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 200,
             "command": "npm test"},
            {"t": "tool_error", "turn": 2, "off": 300,
             "ts": "2026-08-20T00:01:00Z", "text": "Exit code 1\nnpm ERR!"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 400,
             "command": "pnpm test"},
            {"t": "tool", "name": "Bash", "turn": 3, "off": 500,
             "command": "git push origin main"},
            {"t": "tool_error", "turn": 3, "off": 600,
             "ts": "2026-08-20T00:02:00Z", "denial": "user-rejected",
             "text": "The user doesn't want to proceed with this tool use."},
            {"t": "user", "turn": 3, "off": 650,
             "text": "[Request interrupted by user for tool use]"},
            {"t": "user", "turn": 4, "off": 700, "ts": "2026-08-20T00:03:00Z",
             "text": "never push directly, open a PR"},
            {"t": "tool", "name": "Bash", "turn": 5, "off": 800,
             "command": "gh pr create"},
        ]
        s2 = [
            {"t": "user", "turn": 1, "off": 0, "ts": "2026-08-10T00:00:00Z",
             "text": opener},
            {"t": "tool", "name": "Bash", "turn": 1, "off": 100,
             "command": "cat package.json"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 200,
             "command": "npm test"},
            {"t": "tool_error", "turn": 2, "off": 300,
             "ts": "2026-08-10T00:01:00Z", "text": "Exit code 1"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 400,
             "command": "pnpm test"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 450,
             "command": "yarn dev"},
            {"t": "tool_error", "turn": 2, "off": 470,
             "ts": "2026-08-05T00:00:00Z", "text": "yarn: not found"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 490,
             "command": "pnpm dev"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 500,
             "command": "git push origin main"},
            {"t": "tool_error", "turn": 2, "off": 600,
             "ts": "2026-08-10T00:02:00Z", "denial": "user-rejected",
             "text": "The user doesn't want to proceed with this tool use."},
            {"t": "user", "turn": 3, "off": 700, "ts": "2026-08-10T00:03:00Z",
             "text": "no, use pnpm not npm"},
            {"t": "tool", "name": "Bash", "turn": 3, "off": 800,
             "command": "rm -rf node_modules"},
            {"t": "tool_error", "turn": 3, "off": 900,
             "denial": "automode-blocked",
             "text": "Permission for this action was denied by the Claude "
                     "Code auto mode classifier. Reason: …"},
        ]
        s3 = [
            {"t": "user", "turn": 1, "off": 0, "ts": "2026-08-01T00:00:00Z",
             "text": "<command-name>/model</command-name> sidecar noise"},
            {"t": "user", "turn": 1, "off": 10, "ts": "2026-08-01T00:00:01Z",
             "text": "quick fix please"},
            {"t": "tool", "name": "Bash", "turn": 1, "off": 100,
             "command": "cat package.json"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 200,
             "command": "ls -la"},
            {"t": "user", "turn": 2, "off": 300, "ts": "2026-08-01T00:01:00Z",
             "text": "no, use pnpm not npm"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 350,
             "command": "yarn dev"},
            {"t": "tool_error", "turn": 2, "off": 370,
             "ts": "2026-08-01T00:02:00Z", "text": "yarn: not found"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 390,
             "command": "pnpm dev"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 400,
             "command": "cargo build"},
            {"t": "tool_error", "turn": 2, "off": 500,
             "ts": "2026-08-01T00:03:00Z", "text": "error[E0432]"},
            {"t": "tool", "name": "Bash", "turn": 2, "off": 600,
             "command": "echo done"},
        ]
        # s4: the assistant batched two calls before the denial arrived —
        # id-based association must blame `git push`, not the nearest Read
        s4 = [
            {"t": "user", "turn": 1, "off": 0, "ts": "2026-08-01T01:00:00Z",
             "text": "push my branch"},
            {"t": "tool", "name": "Bash", "turn": 1, "off": 50, "id": "aaa111",
             "command": "git push origin main"},
            {"t": "tool", "name": "Read", "turn": 1, "off": 90, "id": "bbb222"},
            {"t": "tool_error", "turn": 1, "off": 130,
             "ts": "2026-08-01T01:01:00Z", "denial": "user-rejected",
             "for_id": "aaa111",
             "text": "The user doesn't want to proceed with this tool use."},
        ]
        for sid, events in (("s1", s1), ("s2", s2), ("s3", s3), ("s4", s4)):
            with open(os.path.join(sdir, sid + ".json"), "w") as f:
                json.dump(events, f)
        with open(os.path.join(self.work, "sessions_index.json"), "w") as f:
            json.dump({"sessions": [
                {"id": "s1", "events": len(s1), "tools": 5,
                 "last_ts": "2026-08-20T00:03:00Z"},
                {"id": "s2", "events": len(s2), "tools": 7,
                 "last_ts": "2026-08-10T00:03:00Z"},
                {"id": "s3", "events": len(s3), "tools": 6,
                 "last_ts": "2026-08-01T00:03:00Z"},
                {"id": "s4", "events": len(s4), "tools": 2,
                 "last_ts": "2026-08-01T01:01:00Z"},
            ]}, f)

    def test_mine_families_gates_and_dedupe(self):
        run("intake.py", "--repo", self.repo, "--work", self.work)
        self._sessions()
        run("mine.py", "--work", self.work)
        c = jload(self.work, "candidates.json")

        texts = [x["text"] for x in c["corrections"]]
        self.assertIn("never push directly, open a PR", texts)
        self.assertEqual(texts.count("no, use pnpm not npm"), 1)  # fork-echo dedupe
        self.assertFalse(any("<command-name>" in t for t in texts))
        push = [x for x in c["corrections"]
                if x["text"].startswith("never push")][0]
        self.assertIn("pivot", push["signals"])
        self.assertIn("after-interrupt", push["signals"])

        pairs = {(p["failed_word"], p["retry_word"]): p
                 for p in c["failure_recovery"]}
        self.assertIn(("npm", "pnpm"), pairs)
        self.assertEqual(pairs[("npm", "pnpm")]["sessions"], 2)
        self.assertIn(("yarn", "pnpm"), pairs)
        self.assertTrue(pairs[("yarn", "pnpm")]["stale"])   # gone from newer half
        self.assertFalse(pairs[("npm", "pnpm")]["stale"])
        self.assertNotIn(("cargo", "echo"), pairs)          # dissimilar: no pair

        redisc = {r["key"]: r for r in c["rediscovery"]}
        self.assertIn("cat package.json", redisc)
        self.assertEqual(redisc["cat package.json"]["sessions"], 3)
        self.assertNotIn("ls", redisc)                      # one session only
        # `git push` recurs early in 3 sessions, so it mechanically survives —
        # deciding it is not "discovery" is the judge's job, not the miner's
        self.assertIn("git push", redisc)

        denials = {(d["kind"], d["key"]): d for d in c["denials"]}
        self.assertIn(("user-rejected", "git"), denials)
        # 3 = id-association worked: s4's batched denial blames git, not Read
        self.assertEqual(denials[("user-rejected", "git")]["sessions"], 3)
        self.assertNotIn(("user-rejected", "Read"), denials)
        self.assertFalse(any(d["kind"] == "automode-blocked"
                             for d in c["denials"]))
        self.assertEqual(c["meta"]["automode_blocked"], 1)

        self.assertEqual(len(c["preambles"]), 1)
        self.assertEqual(c["preambles"][0]["sessions"], 2)
        self.assertTrue(c["preambles"][0]["identical_echo"])

        # tax attributes bytes to the surviving early-command groups (cat ×3
        # sessions + git push ×3, whose union spans all four sessions)
        self.assertEqual(c["startup_tax"]["sessions"], 4)
        self.assertGreater(c["startup_tax"]["est_tokens"], 0)
        # the raw early-window median stays available, clearly labeled
        self.assertEqual(c["startup_tax"]["early_window_median_bytes"], 700)


class TestGenerate(ToyRepo):
    def _chart(self, **over):
        chart = {
            "mode": "intake",
            "facts": [{"text": "Tests: `pnpm test` from the repo root.",
                       "section": "Commands", "family": "rediscovery",
                       "occurrences": 7, "sessions": 5}],
            "rules": [{"id": "MR1", "text": "Use pnpm, never npm.",
                       "family": "failure_recovery", "class": "hook",
                       "occurrences": 4, "sessions": 3,
                       "evidence": [{"session": "abadcafe", "turn": 9,
                                     "excerpt": "npm ERR! … then pnpm install"}]}],
            "startup_tax": {"est_tokens": 30000, "sessions": 12},
            "declined": [{"text": "SECRET-ONE-OFF", "reason": "single occurrence"}],
        }
        chart.update(over)
        with open(os.path.join(self.work, "chart.json"), "w") as f:
            json.dump(chart, f)

    def test_generate_draft_with_receipts(self):
        run("intake.py", "--repo", self.repo, "--work", self.work)
        self._chart(facts=[
            {"text": "Tests: `pnpm test` from the repo root.",
             "section": "Commands", "family": "rediscovery",
             "occurrences": 7, "sessions": 5},
            {"text": "The api lives in services/api --> not apps.",
             "family": "preamble", "occurrences": 3, "sessions": 3},
        ])
        run("generate.py", "--work", self.work)
        draft_path = os.path.join(os.path.dirname(self.work), "PROPOSED-CLAUDE.md")
        with open(draft_path) as f:
            draft = f.read()
        self.assertIn("## Commands", draft)
        self.assertIn("Use pnpm, never npm.", draft)
        self.assertIn("seen 4× across 3 sessions", draft)   # receipt comment
        self.assertIn("hook-enforceable", draft)
        self.assertNotIn("SECRET-ONE-OFF", draft)           # declined never renders
        # unsectioned facts render BEFORE any heading, never under one
        self.assertLess(draft.index("The api lives"), draft.index("## Commands"))
        # a comment delimiter inside body text must not swallow the draft
        self.assertNotIn("--> not apps", draft)
        self.assertIn("--&gt; not apps", draft)
        # adoption is the user's move — nothing lands in the repo root
        self.assertFalse(os.path.exists(os.path.join(self.repo, "PROPOSED-CLAUDE.md")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "CLAUDE.md.proposed")))

    def test_generate_enforces_size_target(self):
        # the doctor must not prescribe the disease it diagnoses
        run("intake.py", "--repo", self.repo, "--work", self.work)
        rules = [{"id": "MR%d" % i, "text": "Rule number %d always applies." % i,
                  "family": "correction", "class": "judge"} for i in range(250)]
        self._chart(rules=rules)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "generate.py"),
                            "--work", self.work], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("OVER the official", r.stdout + r.stderr)

    def test_chart_renders_in_report_and_card(self):
        run("intake.py", "--repo", self.repo, "--work", self.work)
        run("vitals.py", "--work", self.work)
        run("refcheck.py", "--work", self.work)
        self._chart(rules=[
            {"id": "MR1", "text": "Use pnpm, never npm.",
             "family": "failure_recovery", "class": "hook",
             "occurrences": 4, "sessions": 3,
             "evidence": [{"session": "abadcafe", "turn": 9,
                           "excerpt": "npm ERR! … then pnpm install"}]},
            # canaries: model-authored class/provenance must never reach the card
            {"id": "MR2", "text": "SECRET-RULE two", "family": "correction",
             "class": "CLASS-CANARY not an enum", "occurrences": 2,
             "sessions": 2, "provenance": "PROV-CANARY seen in s1"},
        ])
        with open(os.path.join(self.work, "diagnosis.json"), "w") as f:
            json.dump({"grade": "C", "chief_complaint": "no chart on file"}, f)
        out = os.path.join(self.tmp.name, "r.html")
        run("report.py", "--work", self.work, "--out", out)
        with open(out) as f:
            html = f.read()
        self.assertIn("Initial chart", html)
        self.assertIn("failed → fixed", html)
        self.assertIn("SECRET-ONE-OFF", html)   # declined disclosed (report is local)
        run("card.py", "--work", self.work)
        with open(os.path.join(os.path.dirname(self.work), "card.svg")) as f:
            card = f.read()
        self.assertIn("1 fact + 2 rules mined from history", card)
        self.assertIn("The chart was in the history all along.", card)
        for leak in ("pnpm", "SECRET", "abadcafe", "CANARY"):  # aggregates only
            self.assertNotIn(leak, card)


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

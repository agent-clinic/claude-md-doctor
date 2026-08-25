#!/usr/bin/env python3
"""Stage 4b — backtest: replay each rule's matchers over the condensed sessions.

Input is a model-authored <work>/rulebook.json decomposing the memory files
into mechanically checkable rules. The engine is deterministic; the model's
jobs before and after are (a) writing good matchers and (b) sample-verifying
every fire — matchers WILL have bugs, so no result counts until sampled.

Rule schema (all regexes are Python, compiled case-sensitively unless the
pattern itself opts out):
{
  "rules": [{
    "id": "R1", "text": "…", "source": {"file": "…", "line": 46},
    "introduced": "2026-06-01T00:00:00Z",          # optional (git-dated)
    "scope": {"events": ["edit","write"],           # bash|edit|write|tool|assistant|user|tool_error
              "paths": ["src/studio/**"],           # optional, fnmatch vs repo-relative path
              "exclude_paths": ["**/tokens.css"],   # optional
              "repo_only": true},                   # optional: ignore edits outside the repo
    "matchers": {"violation": "…", "compliance": "…", "context": "…"},
    "ordering": {"require": "regex on bash commands",
                 "desc": "run pnpm verify before finishing",
                 "min_mutations": 1}                 # ordering rules need no matchers
  }]
}

Usage: python3 backtest.py --work DIR
Reads:  <work>/rulebook.json, <work>/sessions/*.json
Writes: <work>/backtest.json
"""

import argparse
import fnmatch
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_json, manifest_add, save_json

SAMPLE_V, SAMPLE_C = 6, 3
EDIT_NAMES = {"Edit", "MultiEdit", "NotebookEdit"}


def event_kind(ev):
    if ev["t"] == "tool":
        name = ev.get("name")
        if name == "Bash":
            return "bash"
        if name in EDIT_NAMES:
            return "edit"
        if name == "Write":
            return "write"
        return "tool"
    return ev["t"]  # user | assistant | tool_error


def event_text(ev):
    kind = event_kind(ev)
    if kind == "bash":
        return ev.get("command", "")
    if kind in ("edit", "write"):
        return "PATH: %s\n%s" % (ev.get("file_path", ""), ev.get("new", ""))
    if kind == "tool":
        return "%s %s" % (ev.get("name", ""), " ".join(ev.get("input_keys", [])))
    return ev.get("text", "")


def path_in_scope(ev, repo, scope):
    paths = scope.get("paths")
    excludes = scope.get("exclude_paths") or []
    fp = ev.get("file_path")
    if scope.get("repo_only") and fp and repo \
            and not fp.startswith(repo + os.sep):
        return False  # edits outside the examined repo never count
    if fp:
        rel = os.path.relpath(fp, repo) if fp.startswith(repo + os.sep) else fp
        for pat in excludes:
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(fp, pat):
                return False
        if paths:
            return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(fp, p)
                       for p in paths)
        return True
    return not paths or event_kind(ev) == "bash"  # pathless events pass unless path-scoped


def depth_bucket(turn):
    if turn <= 3:
        return "early"
    return "mid" if turn <= 8 else "late"


def compile_rule(rule):
    m = rule.get("matchers") or {}
    return {k: re.compile(m[k]) for k in ("violation", "compliance", "context")
            if m.get(k)}


def excerpt(text, match, span=90):
    s, e = match.start(), match.end()
    lo, hi = max(0, s - span), min(len(text), e + span)
    return ("…" if lo else "") + text[lo:hi].replace("\n", "⏎") + ("…" if hi < len(text) else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    rulebook = load_json(os.path.join(args.work, "rulebook.json"))
    intake = load_json(os.path.join(args.work, "intake.json")) or {}
    index = load_json(os.path.join(args.work, "sessions_index.json")) or {}
    if not rulebook or not rulebook.get("rules"):
        sys.exit("backtest: missing or empty rulebook.json (write it first — see SKILL.md stage 4)")
    repo = intake.get("repo", "")
    sess_dir = os.path.join(args.work, "sessions")
    sessions = [s for s in index.get("sessions", []) if s.get("events")]

    stats = {}
    for rule in rulebook["rules"]:
        stats[rule["id"]] = {
            "text": rule.get("text", ""), "source": rule.get("source"),
            "opportunities": 0, "violations": 0, "compliances": 0,
            "pre_rule_sessions": 0, "sessions_with_activity": 0,
            "violations_by_depth": {"early": 0, "mid": 0, "late": 0},
            "samples": {"violations": [], "compliances": []},
        }

    for sess in sessions:
        events = load_json(os.path.join(sess_dir, sess["id"] + ".json")) or []
        for rule in rulebook["rules"]:
            st = stats[rule["id"]]
            pre_rule = bool(rule.get("introduced")) and \
                bool(sess.get("last_ts")) and sess["last_ts"] < rule["introduced"]
            if pre_rule:
                st["pre_rule_sessions"] += 1
            rx = compile_rule(rule)
            scope = rule.get("scope") or {}
            kinds = set(scope.get("events") or ["bash", "edit", "write"])
            active = False

            if rule.get("ordering"):
                o = rule["ordering"]
                req = re.compile(o["require"])
                last_mut, req_after = -1, False
                mutations = 0
                tail = []
                for i, ev in enumerate(events):
                    k = event_kind(ev)
                    if k in ("edit", "write") and path_in_scope(ev, repo, scope):
                        last_mut, mutations, req_after = i, mutations + 1, False
                    elif k == "bash":
                        tail.append(ev.get("command", "")[:120])
                        if req.search(ev.get("command", "")) and i > last_mut:
                            req_after = True
                if mutations >= o.get("min_mutations", 1) and not pre_rule:
                    st["opportunities"] += 1
                    active = True
                    if req_after:
                        st["compliances"] += 1
                        if len(st["samples"]["compliances"]) < SAMPLE_C:
                            st["samples"]["compliances"].append(
                                {"session": sess["id"],
                                 "note": "%d file edits; required command ran afterwards" % mutations})
                    else:
                        st["violations"] += 1
                        st["violations_by_depth"]["late"] += 1
                        if len(st["samples"]["violations"]) < SAMPLE_V:
                            st["samples"]["violations"].append(
                                {"session": sess["id"], "turn": events[-1].get("turn", 0),
                                 "note": "session ended after %d file edits without: %s"
                                         % (mutations, o.get("desc", o["require"])),
                                 "excerpt": " | ".join(tail[-3:]) or "(no shell commands)"})
            else:
                for i, ev in enumerate(events):
                    if event_kind(ev) not in kinds or not path_in_scope(ev, repo, scope):
                        continue
                    text = event_text(ev)
                    vm = rx.get("violation").search(text) if rx.get("violation") else None
                    cm = rx.get("compliance").search(text) if rx.get("compliance") else None
                    xm = rx.get("context").search(text) if rx.get("context") else None
                    if not (vm or cm or xm) or pre_rule:
                        continue
                    st["opportunities"] += 1
                    active = True
                    if vm and not cm:
                        st["violations"] += 1
                        st["violations_by_depth"][depth_bucket(ev.get("turn", 0))] += 1
                        if len(st["samples"]["violations"]) < SAMPLE_V:
                            st["samples"]["violations"].append(
                                {"session": sess["id"], "turn": ev.get("turn", 0),
                                 "event": event_kind(ev),
                                 "file": ev.get("file_path"),
                                 "excerpt": excerpt(text, vm)})
                    elif cm:
                        st["compliances"] += 1
                        if len(st["samples"]["compliances"]) < SAMPLE_C:
                            st["samples"]["compliances"].append(
                                {"session": sess["id"], "turn": ev.get("turn", 0),
                                 "excerpt": excerpt(text, cm)})
            if active:
                st["sessions_with_activity"] += 1

    out = {
        "window": {
            "sessions_replayed": len(sessions),
            "stub_sessions_skipped": len(index.get("sessions", [])) - len(sessions),
            "total_events": sum(s.get("events", 0) for s in sessions),
            "total_tool_calls": sum(s.get("tools", 0) for s in sessions),
            "from": min((s.get("first_ts") or "" for s in sessions), default=None),
            "to": max((s.get("last_ts") or "" for s in sessions), default=None),
            "machine_note": "this machine's transcripts only; bounded by cleanupPeriodDays",
        },
        "per_rule": stats,
        "verified": False,  # flipped by the model after the sample-verification pass
    }
    save_json(os.path.join(args.work, "backtest.json"), out)
    manifest_add(args.work, "backtest", rules=len(stats),
                 sessions=len(sessions))
    for rid, st in stats.items():
        print("%-4s opp=%-3d viol=%-3d comp=%-3d  %s"
              % (rid, st["opportunities"], st["violations"], st["compliances"],
                 st["text"][:60]))
    print("backtest: %d rules x %d sessions -> backtest.json (now SAMPLE-VERIFY before trusting)"
          % (len(stats), len(sessions)))


if __name__ == "__main__":
    main()

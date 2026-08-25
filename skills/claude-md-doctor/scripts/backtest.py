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
                 "min_mutations": 1},                # ordering rules need no matchers
    "origin": "root",                                # root|nested|rules|conversation —
                                                     # only non-root rules can be truly
                                                     # absent post-compact
    "enforcement": {                                 # v0.3 classification (model-authored)
      "class": "hook",                               # hook|linter|test|judge
      "subtype": "bash-gate",                        # e.g. bash-gate|edit-gate|stop-gate|
                                                     #      tool-input-gate|output-gate
      "scope_kind": "file",                          # file|project (linter class)
      "current_layer": "prose",                      # prose, or the existing enforcement
                                                     # (hook|linter|test|ci) the prose points at
      "mechanism": "PreToolUse Bash regex",          # named mechanism for the prescription
      "echo_regex": "pnpm verify|No exceptions"      # distinctive tokens: an assistant-text
    }                                                # match BEFORE a violation = proven defiance
  }]
}

Each violation is triaged by context state into a cause —
defiance-proven (rule echoed in the agent's own words, then violated) >
defiance (fresh context) > dilution (late turn / heavy context) >
absence-risk (non-root rule after a compaction boundary) — and each rule gets
an arming recommendation (reminder → warn-hook → block) derived from its
cause mix. Occupancy is proxied by raw-transcript byte offsets; compaction
boundaries come from the transcript's own markers.

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
DILUTION_TURN = 9          # violations past this turn lean dilution (SysBench/McMillan)
DILUTION_BYTES = 400_000   # raw-transcript bytes since last compaction ≈ heavy context


class SessionContext(object):
    """Per-session context-state features for cause triage."""

    def __init__(self, events):
        self.compact_offs = [e.get("off", 0) for e in events if e["t"] == "compact"]
        self.assistant_texts = [(i, e.get("text", "")) for i, e in enumerate(events)
                                if e["t"] == "assistant"]

    def epoch_start(self, off):
        prior = [c for c in self.compact_offs if c <= off]
        return max(prior) if prior else 0

    def post_compact(self, off):
        return any(c <= off for c in self.compact_offs)

    def echoed_before(self, rx, idx):
        return bool(rx) and any(rx.search(t) for i, t in self.assistant_texts
                                if i < idx and t)


def cause_of(rule, rx_echo, ev, idx, ctx):
    off = ev.get("off", 0)
    if ctx.echoed_before(rx_echo, idx):
        return "defiance-proven"
    if rule.get("origin", "root") != "root" and ctx.post_compact(off):
        return "absence-risk"
    if ev.get("turn", 0) > DILUTION_TURN or \
            (off - ctx.epoch_start(off)) > DILUTION_BYTES:
        return "dilution"
    return "defiance"


def recommend_arming(st, enf):
    cls = (enf or {}).get("class")
    cur = (enf or {}).get("current_layer") or "prose"
    if cur != "prose":
        return "already enforced (%s) — prose is the pointer; verify it still runs" % cur
    if cls == "judge":
        return "judge-class: stays prose; audited by backtest, reliability ceiling applies"
    if cls not in ("hook", "linter", "test"):
        return "unclassified — classify before arming"
    v, c = st["violations"], st["causes"]
    if v == 0:
        return ("healthy in window — enforcement optional" if st["compliances"]
                else "inert in window — no arming evidence either way")
    if c.get("defiance-proven"):
        return "BLOCK-ready: rule was echoed then violated — the reminder already happened and lost"
    half = max(1, v / 2.0)
    if c.get("defiance", 0) >= half:
        return "arm warn-mode now; graduate to block after a clean warn period"
    if c.get("dilution", 0) >= half:
        return "soft first: slim the file / path-scope to point of use / PostToolUse nudge"
    if c.get("absence-risk", 0) >= half:
        return "re-inject: SessionStart or PreCompact hook, or a path-scoped rule"
    return "mixed causes — warn-mode hook and re-triage next run"


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


ENV_PREFIX_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=(?:\"[^\"]*\"|'[^']*'|\S+)\s+)+")


def command_word(cmd):
    """First meaningful word of a shell command: split compound commands on
    && / ; / |, strip env-assignment prefixes, take the first real word."""
    for seg in re.split(r"&&|\|\||;|\|", cmd or ""):
        seg = ENV_PREFIX_RE.sub("", seg.strip())
        words = seg.split()
        if words and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]):
            return os.path.basename(words[0])[:24]
    return "?"


def build_timeline(tool_seq, last_mut, last_mut_turn, mutations):
    """Run-length encode the session's tool sequence for the report's strip
    visualization, and summarize what ran after the last mutation."""
    segments, after_counts = [], {}
    for kind, idx, word in tool_seq:
        after = idx > last_mut
        if segments and segments[-1]["k"] == kind and segments[-1]["after"] == after:
            segments[-1]["n"] += 1
        else:
            segments.append({"k": kind, "n": 1, "after": after})
        if after and kind == "bash" and word:
            after_counts[word] = after_counts.get(word, 0) + 1
    if len(segments) > 60:  # keep the strip drawable
        head, tail = segments[:30], segments[-29:]
        merged = {"k": "other", "n": sum(s["n"] for s in segments[30:-29]),
                  "after": tail[0]["after"] if tail else False}
        segments = head + [merged] + tail
    return {"segments": segments, "edits": mutations,
            "last_edit_turn": last_mut_turn,
            "after_cmds": sorted(after_counts.items(),
                                 key=lambda kv: -kv[1])[:5]}


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
            "causes": {}, "enforcement": rule.get("enforcement"),
            "origin": rule.get("origin", "root"),
            "samples": {"violations": [], "compliances": []},
        }

    for sess in sessions:
        events = load_json(os.path.join(sess_dir, sess["id"] + ".json")) or []
        ctx = SessionContext(events)
        for rule in rulebook["rules"]:
            st = stats[rule["id"]]
            echo_pat = (rule.get("enforcement") or {}).get("echo_regex")
            rx_echo = re.compile(echo_pat) if echo_pat else None

            def tally_cause(ev, idx):
                cause = cause_of(rule, rx_echo, ev, idx, ctx)
                st["causes"][cause] = st["causes"].get(cause, 0) + 1
                return cause
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
                last_mut, last_mut_turn, req_after = -1, 0, False
                mutations = 0
                tool_seq = []  # (kind, event index, command-word or None)
                for i, ev in enumerate(events):
                    k = event_kind(ev)
                    if k in ("edit", "write") and path_in_scope(ev, repo, scope):
                        last_mut, mutations, req_after = i, mutations + 1, False
                        last_mut_turn = ev.get("turn", 0)
                        tool_seq.append(("edit", i, None))
                    elif k == "bash":
                        cmd = ev.get("command", "")
                        tool_seq.append(("bash", i, command_word(cmd)))
                        if req.search(cmd) and i > last_mut:
                            req_after = True
                    elif k in ("write", "edit", "tool"):
                        tool_seq.append(("other", i, None))
                if mutations >= o.get("min_mutations", 1) and not pre_rule:
                    st["opportunities"] += 1
                    active = True
                    viz = build_timeline(tool_seq, last_mut, last_mut_turn,
                                         mutations)
                    if req_after:
                        st["compliances"] += 1
                        if len(st["samples"]["compliances"]) < SAMPLE_C:
                            st["samples"]["compliances"].append(
                                {"session": sess["id"], "ok": True, "viz": viz,
                                 "note": "%d file edits; required command ran afterwards" % mutations})
                    else:
                        st["violations"] += 1
                        st["violations_by_depth"]["late"] += 1
                        # cause is judged where the obligation ripened — the
                        # last mutation — not at session end
                        ripen = last_mut if last_mut >= 0 else len(events) - 1
                        cause = tally_cause(events[ripen], len(events) - 1)
                        if len(st["samples"]["violations"]) < SAMPLE_V:
                            st["samples"]["violations"].append(
                                {"session": sess["id"], "turn": events[-1].get("turn", 0),
                                 "viz": viz, "cause": cause,
                                 "note": "session ended after %d file edits without: %s"
                                         % (mutations, o.get("desc", o["require"]))})
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
                        cause = tally_cause(ev, i)
                        if len(st["samples"]["violations"]) < SAMPLE_V:
                            st["samples"]["violations"].append(
                                {"session": sess["id"], "turn": ev.get("turn", 0),
                                 "event": event_kind(ev), "cause": cause,
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

    for rid, st in stats.items():
        st["arming"] = recommend_arming(st, st["enforcement"])

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

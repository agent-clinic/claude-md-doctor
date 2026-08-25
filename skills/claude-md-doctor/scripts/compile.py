#!/usr/bin/env python3
"""Stage 4e — compile: turn backtested rules into review-then-arm enforcement
proposals. NOTHING here is installed automatically — hooks execute shell, so
every artifact lands in <work>/enforcement/ for a human to read, edit, and
wire in themselves. Matchers were validated against real history first
("backtest before you arm"); the arming level per rule comes from its
violation-cause mix.

Emits:
  enforcement/PROPOSALS.md          — per-rule dossier: class, evidence, arming, snippet
  enforcement/rules-guard.json      — machine config for the generic guard
  enforcement/claude_md_doctor_guard.py — generic PreToolUse guard (warn|block per rule)
  enforcement/settings-snippet.json — hooks fragment to merge into .claude/settings.json

Usage: python3 compile.py --work DIR
Reads:  <work>/rulebook.json, <work>/backtest.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_json, manifest_add, save_json

GUARD = '''#!/usr/bin/env python3
"""claude-md-doctor generated PreToolUse guard — REVIEW BEFORE ARMING.

Reads the hook payload on stdin, applies the regexes in rules-guard.json to
Bash commands and Edit/Write content, and per rule either warns (stderr,
non-blocking) or blocks (exit 2 — Claude sees the message and must adjust).
Flip a rule's "mode" between "warn" and "block" in rules-guard.json.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(HERE, "rules-guard.json")))
payload = json.load(sys.stdin)
tool = payload.get("tool_name", "")
inp = payload.get("tool_input") or {}
if tool == "Bash":
    text = inp.get("command", "")
    kind = "bash"
elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
    text = "PATH: %s\\n%s" % (inp.get("file_path", ""),
                              inp.get("new_string") or inp.get("content") or "")
    kind = "edit"
else:
    sys.exit(0)

blocked = []
for rule in cfg["rules"]:
    if kind not in rule.get("kinds", ["bash", "edit"]):
        continue
    if re.search(rule["violation"], text):
        msg = "[claude-md-doctor guard] %s: %s (%s)" % (
            rule["id"], rule["text"], rule.get("source", ""))
        if rule.get("mode") == "block":
            blocked.append(msg)
        else:
            print(msg + " — warning only", file=sys.stderr)
if blocked:
    print("\\n".join(blocked), file=sys.stderr)
    sys.exit(2)
'''

SETTINGS_SNIPPET = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash|Edit|Write|MultiEdit",
                "hooks": [
                    {"type": "command",
                     "command": "python3 .claude/hooks/claude_md_doctor_guard.py"}
                ]
            }
        ]
    }
}


def dossier(rule, st):
    enf = rule.get("enforcement") or {}
    lines = ["## %s — %s" % (rule["id"], rule.get("text", "")), ""]
    lines.append("- **Class**: %s%s · scope %s · today: %s"
                 % (enf.get("class", "unclassified"),
                    " (%s)" % enf["subtype"] if enf.get("subtype") else "",
                    enf.get("scope_kind", "file"),
                    enf.get("current_layer", "prose")))
    if enf.get("mechanism"):
        lines.append("- **Mechanism**: %s" % enf["mechanism"])
    if st:
        causes = ", ".join("%s ×%d" % (k, v)
                           for k, v in sorted(st.get("causes", {}).items())) or "none"
        lines.append("- **Backtest evidence**: %d opportunities, %d violations "
                     "(%s), %d compliances"
                     % (st.get("opportunities", 0), st.get("violations", 0),
                        causes, st.get("compliances", 0)))
        lines.append("- **Recommended arming**: %s" % st.get("arming", "n/a"))
    m = rule.get("matchers") or {}
    if enf.get("class") == "hook" and m.get("violation"):
        lines.append("- **Guard entry** (added to rules-guard.json, mode `warn`):")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(guard_entry(rule, st), indent=2))
        lines.append("```")
    elif enf.get("class") in ("linter", "test"):
        lines.append("- **Encode it**: %s — this binds every agent and every "
                     "human; prose then becomes a one-line pointer."
                     % (enf.get("mechanism") or "add a lint rule / discipline test"))
    elif rule.get("ordering"):
        lines.append("- **Stop-gate candidate**: enforce '%s' with a Stop hook "
                     "that checks the session transcript for the required "
                     "command after the last file edit (template in PROPOSALS "
                     "header)." % rule["ordering"].get("desc", ""))
    lines.append("")
    return "\n".join(lines)


def guard_entry(rule, st):
    scope = rule.get("scope") or {}
    kinds = []
    for e in scope.get("events", []):
        if e == "bash":
            kinds.append("bash")
        if e in ("edit", "write"):
            kinds.append("edit")
    mode = "warn"
    if st and st.get("causes", {}).get("defiance-proven"):
        mode = "block"
    return {"id": rule["id"], "text": rule.get("text", "")[:100],
            "source": "%s:%s" % ((rule.get("source") or {}).get("file", "?"),
                                 (rule.get("source") or {}).get("line", "?")),
            "kinds": sorted(set(kinds)) or ["bash", "edit"],
            "violation": rule["matchers"]["violation"],
            "mode": mode}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    rulebook = load_json(os.path.join(args.work, "rulebook.json"))
    backtest = load_json(os.path.join(args.work, "backtest.json")) or {}
    if not rulebook:
        sys.exit("compile: missing rulebook.json")
    per_rule = backtest.get("per_rule", {})
    out_dir = os.path.join(args.work, "enforcement")
    os.makedirs(out_dir, exist_ok=True)

    hook_rules = [r for r in rulebook["rules"]
                  if (r.get("enforcement") or {}).get("class") == "hook"
                  and (r.get("matchers") or {}).get("violation")
                  and ((r.get("enforcement") or {}).get("current_layer")
                       or "prose") == "prose"]
    guard_cfg = {"_note": "REVIEW EACH ENTRY BEFORE ARMING. mode: warn|block.",
                 "rules": [guard_entry(r, per_rule.get(r["id"])) for r in hook_rules]}

    head = [
        "# Enforcement proposals — REVIEW BEFORE ARMING",
        "",
        "Generated by claude-md-doctor from rules validated against this repo's",
        "own session history (matchers were sample-verified; arming levels come",
        "from each rule's violation-cause mix). Nothing here is installed",
        "automatically. To arm the guard:",
        "",
        "1. Read every entry below and `rules-guard.json`.",
        "2. Copy `claude_md_doctor_guard.py` and `rules-guard.json` into "
        "`.claude/hooks/`.",
        "3. Merge `settings-snippet.json` into `.claude/settings.json`.",
        "4. Rules default to `warn`; flip to `block` only after a clean warn "
        "period (defiance-proven rules start at block — the reminder already "
        "happened and lost).",
        "",
        "Evidence: prose/memory alone leaves large violation rates even when the",
        "rule is demonstrably seen (TRACE arXiv:2606.13174: 57.5% violated with",
        "memory access; compiled checks cut violations to 2–38%). Hooks are the",
        "official mechanism for must-happen rules.",
        "", "---", "",
    ]
    body = [dossier(r, per_rule.get(r["id"])) for r in rulebook["rules"]]

    with open(os.path.join(out_dir, "PROPOSALS.md"), "w") as f:
        f.write("\n".join(head + body))
    save_json(os.path.join(out_dir, "rules-guard.json"), guard_cfg)
    with open(os.path.join(out_dir, "claude_md_doctor_guard.py"), "w") as f:
        f.write(GUARD)
    save_json(os.path.join(out_dir, "settings-snippet.json"), SETTINGS_SNIPPET)

    manifest_add(args.work, "compile", hook_rules=len(hook_rules),
                 total_rules=len(rulebook["rules"]))
    print("compile: %d rule dossier(s), %d guard entr%s -> %s"
          % (len(rulebook["rules"]), len(hook_rules),
             "y" if len(hook_rules) == 1 else "ies", out_dir))


if __name__ == "__main__":
    main()

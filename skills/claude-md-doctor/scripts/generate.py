#!/usr/bin/env python3
"""Stage B4 — generate: assemble a proposed CLAUDE.md from the curated chart.

Input is a model-authored <work>/chart.json: the judged survivors of the
history mining (mine.py found candidates; the model kept only recurrent,
still-current ones and wrote receipts). This script is a deterministic
assembler — it adds nothing, it only formats what the chart contains, and it
holds the draft to the same vitals this tool diagnoses in other people's
files: a draft over the official 200-line target is an error, not a warning.

Provenance rides in HTML comments (`<!-- seen 4× across 3 sessions -->`) —
Claude Code strips those at load, so receipts cost the reviewer nothing.

chart.json schema (model-authored):
{
  "mode": "intake",                    # intake = no memory file exists;
                                       # gap = additions to an existing file
  "facts": [{"text": "Tests: `pnpm test:unit` from the repo root.",
             "section": "Commands",    # optional grouping heading
             "family": "rediscovery",  # correction|failure_recovery|
                                       # rediscovery|denial|preamble
             "occurrences": 7, "sessions": 5,
             "provenance": "optional override for the receipt comment",
             "evidence": [{"session": "…", "turn": 3, "excerpt": "…"}]}],
  "rules": [{"id": "MR1", "text": "Use pnpm, never npm.",
             "family": "failure_recovery",
             "class": "hook",          # hook|linter|test|judge (taxonomy)
             "occurrences": 4, "sessions": 3,
             "evidence": [{"session": "…", "turn": 9, "excerpt": "…"}]}],
  "startup_tax": {"est_tokens": 30000, "sessions": 12},   # optional
  "declined": [{"text": "…", "reason": "one-off / stale since July"}]
}
`family` values are singular (they key report.py's labels); candidates.json's
top-level keys are the plural family names — map corrections→correction,
denials→denial, preambles→preamble when carrying items over.

Usage: python3 generate.py --work DIR [--out FILE]
Reads:  <work>/chart.json, <work>/intake.json
Writes: <work>/../PROPOSED-CLAUDE.md   (mode intake)
        <work>/../PROPOSED-ADDITIONS.md (mode gap)
Never writes into the repo root — adoption is the user's move.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_json, manifest_add
from vitals import SIZE_TARGET_LINES, measure

LEAN_TARGET_LINES = 60  # a mined draft should be far under the official cap


def receipt(item):
    if item.get("provenance"):
        # "--" inside an HTML comment ends or corrupts it
        return item["provenance"].replace("--", "–")
    n, s = item.get("occurrences"), item.get("sessions")
    if n and s:
        return "seen %d× across %d session%s" % (n, s, "" if s == 1 else "s")
    return "mined from session history"


def body_text(s):
    """Fact/rule text goes OUTSIDE comments — but a stray comment delimiter
    in it would swallow the rest of the draft at load time."""
    return s.rstrip().replace("<!--", "&lt;!--").replace("-->", "--&gt;")


def render(chart, repo_name, sessions_n):
    mode = chart.get("mode", "intake")
    lines = []
    if mode == "intake":
        lines.append("# %s" % repo_name)
    else:
        lines.append("# Proposed additions to CLAUDE.md")
    lines += [
        "",
        "<!-- Proposed by claude-md-doctor from %d session(s) of this repo's"
        % sessions_n,
        "     own history. Every line below recurred in real sessions; receipts",
        "     are in report.html. Review each one — delete anything you would",
        "     not bet on — then %s. -->"
        % ("save as CLAUDE.md in the repo root" if mode == "intake"
           else "merge into the existing file"),
        "",
    ]

    # Facts, grouped by their optional section heading. Unsectioned facts
    # always render FIRST — after a heading they would silently read as
    # members of the previous section.
    sections, order = {}, []
    for f in chart.get("facts", []):
        key = f.get("section") or ""
        if key not in sections:
            sections[key] = []
            order.append(key)
        sections[key].append(f)
    for key in ([""] if "" in sections else []) + [k for k in order if k]:
        if key:
            lines += ["## %s" % key, ""]
        for f in sections[key]:
            lines.append("%s <!-- %s -->" % (body_text(f["text"]), receipt(f)))
        lines.append("")

    rules = chart.get("rules", [])
    if rules:
        lines += ["## Rules", ""]
        for r in rules:
            note = receipt(r)
            if r.get("class") == "hook":
                note += "; hook-enforceable — guard proposal in the exam folder"
            elif r.get("class") in ("linter", "test"):
                note += "; better as a lint rule/test — see the report"
            lines.append("- %s <!-- %s -->" % (body_text(r["text"]), note))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    # normalize: with a relative --work like ".", dirname("") would drop the
    # draft INSIDE the work dir instead of next to the report
    args.work = os.path.abspath(args.work)
    chart = load_json(os.path.join(args.work, "chart.json"))
    intake = load_json(os.path.join(args.work, "intake.json")) or {}
    if not chart:
        sys.exit("generate: missing chart.json (write it first — see SKILL.md Mode B)")
    if not (chart.get("facts") or chart.get("rules")):
        sys.exit("generate: chart.json has no facts and no rules — nothing to propose")
    mode = chart.get("mode", "intake")

    index = load_json(os.path.join(args.work, "sessions_index.json")) or {}
    sessions_n = len([s for s in index.get("sessions", []) if s.get("events")])
    repo_name = os.path.basename(intake.get("repo", "")) or "This repository"

    name = "PROPOSED-CLAUDE.md" if mode == "intake" else "PROPOSED-ADDITIONS.md"
    out_path = args.out or os.path.join(os.path.dirname(args.work), name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render(chart, repo_name, sessions_n))

    m = measure(out_path) or {}
    eff, toks = m.get("effective_lines", 0), m.get("est_tokens", 0)
    over = mode == "intake" and eff > SIZE_TARGET_LINES
    manifest_add(args.work, "generate", mode=mode, out=out_path,
                 facts=len(chart.get("facts", [])),
                 rules=len(chart.get("rules", [])),
                 effective_lines=eff, over_target=over)
    print("generate: %s — %d fact(s), %d rule(s), %d effective lines (~%d tokens)"
          % (out_path, len(chart.get("facts", [])),
             len(chart.get("rules", [])), eff, toks))
    if over:
        # the doctor must not prescribe the disease it diagnoses
        sys.exit("generate: draft is %d effective lines — OVER the official "
                 "%d-line target this tool exists to enforce. Trim chart.json "
                 "(keep only rules you would bet on) and re-run." %
                 (eff, SIZE_TARGET_LINES))
    if eff > LEAN_TARGET_LINES:
        print("generate: note — %d lines is legal but not lean; a mined draft "
              "usually earns under %d" % (eff, LEAN_TARGET_LINES))


if __name__ == "__main__":
    main()

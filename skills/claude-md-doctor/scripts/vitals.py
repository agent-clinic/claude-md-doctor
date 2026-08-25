#!/usr/bin/env python3
"""Stage 2 — vitals: size, structure, and pathology markers for each memory file.

Official thresholds (cited in the report): 200 lines per file (memory doc),
40,000-char combined startup warning, 4 MiB per-file hard skip. Effective lines
are measured after stripping block HTML comments, matching Claude Code's loader.

Usage: python3 vitals.py --work DIR
Reads:  <work>/intake.json    Writes: <work>/vitals.json
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (est_tokens, iter_lines, load_json, manifest_add,
                     read_text, save_json, strip_html_comments)

SIZE_TARGET_LINES = 200          # official: memory doc
STARTUP_WARN_CHARS = 40_000      # official: troubleshooting doc
HARD_SKIP_BYTES = 4 * 1024 * 1024  # official: memory doc
CONTEXT_BUDGET_TOKENS = 200_000  # typical window, for the %-of-context vital

EMPHASIS_RE = re.compile(r"\b(NEVER|ALWAYS|IMPORTANT|CRITICAL|MUST|DO NOT|DON'T)\b")
BOLD_RE = re.compile(r"\*\*[^*\n]+\*\*")
INIT_BOILERPLATE_RE = re.compile(r"provides guidance to Claude Code", re.I)
DATE_RE = re.compile(
    r"\b(20\d{2}-\d{2}(-\d{2})?|"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+20\d{2})\b")
IMPERATIVE_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(Use|Run|Never|Always|Do|Don't|Avoid|Prefer|Keep|Add|"
    r"Check|Read|Write|Test|Set|Follow|Ask|Stop|Only|Wrap|Put|See)\b", re.I)


def heading_stats(text):
    heads, stack = [], []
    for lineno, line, in_fence in iter_lines(text):
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            heads.append({"level": len(m.group(1)), "text": m.group(2).strip(),
                          "line": lineno})
    dupes = {}
    for h in heads:
        dupes.setdefault(h["text"].lower(), []).append(h["line"])
    duplicate_headings = [{"text": t, "lines": ls} for t, ls in dupes.items()
                          if len(ls) > 1]
    # longest section = gap between consecutive headings
    longest = None
    total_lines = text.count("\n") + 1
    for i, h in enumerate(heads):
        end = heads[i + 1]["line"] - 1 if i + 1 < len(heads) else total_lines
        span = end - h["line"]
        if longest is None or span > longest["lines"]:
            longest = {"heading": h["text"], "start_line": h["line"], "lines": span}
    return heads, duplicate_headings, longest


def measure(path):
    raw = read_text(path)
    if raw is None:
        return None
    clean, comment_lines_removed = strip_html_comments(raw)
    lines = clean.splitlines()
    eff_lines = len([l for l in lines if l.strip()])
    chars = len(clean)
    heads, dupes, longest = heading_stats(clean)

    emphasis_lines = bold_lines = dated_lines = imperative_lines = fence_lines = 0
    in_prose_lines = 0
    for _, line, in_fence in iter_lines(clean):
        if in_fence:
            fence_lines += 1
            continue
        if not line.strip():
            continue
        in_prose_lines += 1
        if EMPHASIS_RE.search(line):
            emphasis_lines += 1
        if BOLD_RE.search(line):
            bold_lines += 1
        if DATE_RE.search(line):
            dated_lines += 1
        if IMPERATIVE_RE.match(line) or re.search(r"\b(must|should|never|always)\b",
                                                  line, re.I):
            imperative_lines += 1

    head_text = "\n".join(clean.splitlines()[:5])
    per100 = (lambda n: round(100.0 * n / eff_lines, 1) if eff_lines else 0.0)
    return {
        "raw_lines": raw.count("\n") + 1,
        "effective_lines": eff_lines,
        "comment_lines_removed": comment_lines_removed,
        "chars": chars,
        "est_tokens": est_tokens(chars),
        "size_bytes": len(raw.encode("utf-8", "replace")),
        "over_size_target": eff_lines > SIZE_TARGET_LINES,
        "over_hard_skip": len(raw.encode("utf-8", "replace")) > HARD_SKIP_BYTES,
        "headings": len(heads),
        "max_heading_level": max([h["level"] for h in heads], default=0),
        "duplicate_headings": dupes,
        "longest_section": longest,
        "code_fence_lines": fence_lines,
        "emphasis_lines": emphasis_lines,
        "emphasis_per_100_lines": per100(emphasis_lines),
        "bold_lines": bold_lines,
        "dated_lines": dated_lines,
        "dated_per_100_lines": per100(dated_lines),
        "imperative_lines": imperative_lines,
        "imperative_ratio": round(imperative_lines / in_prose_lines, 2)
                            if in_prose_lines else 0.0,
        "init_boilerplate": bool(INIT_BOILERPLATE_RE.search(head_text)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    intake = load_json(os.path.join(args.work, "intake.json"))
    if not intake:
        sys.exit("vitals: run intake.py first (missing intake.json)")

    per_file, combined = {}, {"effective_lines": 0, "chars": 0, "est_tokens": 0}
    for rec in intake["files"]:
        if not rec["exists"] or rec["excluded"]:
            continue
        m = measure(rec["path"])
        if m is None:
            continue
        m["scope"] = rec["scope"]
        m["loaded_at_launch"] = rec["loaded_at_launch"]
        m["external"] = rec["external"]
        m["is_pointer"] = rec.get("is_pointer", False)
        per_file[rec["path"]] = m
        if rec["path"] in intake["effective_launch_loaded"]:
            for k in combined:
                combined[k] += m[{"effective_lines": "effective_lines",
                                  "chars": "chars",
                                  "est_tokens": "est_tokens"}[k]]

    combined["pct_of_context"] = round(
        100.0 * combined["est_tokens"] / CONTEXT_BUDGET_TOKENS, 2)
    combined["startup_warning"] = combined["chars"] > STARTUP_WARN_CHARS
    out = {
        "thresholds": {"size_target_lines": SIZE_TARGET_LINES,
                       "startup_warn_chars": STARTUP_WARN_CHARS,
                       "hard_skip_bytes": HARD_SKIP_BYTES,
                       "context_budget_tokens": CONTEXT_BUDGET_TOKENS},
        "per_file": per_file,
        "launch_loaded_combined": combined,
    }
    save_json(os.path.join(args.work, "vitals.json"), out)
    manifest_add(args.work, "vitals", files_measured=len(per_file))
    print("vitals: measured %d files; launch-loaded total %d effective lines, "
          "~%d tokens (%.2f%% of a %dk context) -> vitals.json"
          % (len(per_file), combined["effective_lines"], combined["est_tokens"],
             combined["pct_of_context"], CONTEXT_BUDGET_TOKENS // 1000))


if __name__ == "__main__":
    main()

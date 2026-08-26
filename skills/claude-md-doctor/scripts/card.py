#!/usr/bin/env python3
"""Stage 6b — share card + health badge.

Generates two SHARE-SAFE artifacts next to report.html:

  card.svg              — a postable 800x418 checkup card: grade, pixel
                          hearts, a one-line doctor's note, aggregate stats,
                          class-distribution bar. Contains NO file paths, NO
                          rule text, NO quotes from the repo, NO session ids —
                          aggregates only. The repo NAME is shown (the card
                          exists to be posted); pass --anonymous to omit it.
  claude-md-health.svg  — a flat README badge ("CLAUDE.md checkup | B")
                          colored by grade, for the coverage-badge loop.

The doctor's note comes from diagnosis.json's optional `share_note` (the
model writes it under strict safety rules — see SKILL.md), with dry,
deterministic fallbacks keyed to the stats.

Usage: python3 card.py --work DIR [--name NAME] [--anonymous]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_json, manifest_add

PAL = {"bg": "#f6f7f5", "card": "#ffffff", "line": "#d8dcd6", "ink": "#1c2024",
       "ink2": "#5b6470", "ink3": "#8a93a0", "accent": "#2f6f5e",
       "warn": "#9a6d1f", "crit": "#b23c2e", "info": "#5f8fc9"}
GRADE_COLOR = {"A": "#2c7a5c", "B": "#2f6f5e", "C": "#9a6d1f",
               "D": "#b23c2e", "F": "#b23c2e"}
CLASS_COLOR = {"hook": "#2f6f5e", "linter": "#5f8fc9", "test": "#5f8fc9",
               "judge": "#d4a04c", "unclassified": "#8a93a0"}

BOT = """<g shape-rendering="crispEdges" transform="translate(%d,%d) scale(%s)">
<rect x="28" y="0" width="8" height="4" fill="#5fd4c8"/><rect x="30" y="4" width="4" height="4" fill="#93a0af"/>
<rect x="12" y="8" width="40" height="24" fill="#93a0af"/>
<rect x="40" y="8" width="4" height="4" fill="#d4a04c"/><rect x="44" y="4" width="8" height="8" fill="#d4a04c"/><rect x="46" y="6" width="4" height="4" fill="#fdfdfc"/>
<rect x="16" y="16" width="32" height="8" fill="#2b3440"/>
<rect x="20" y="18" width="6" height="4" fill="#5fd4c8"/><rect x="38" y="18" width="6" height="4" fill="#5fd4c8"/>
<rect x="26" y="27" width="12" height="2" fill="#2b3440"/>
<rect x="26" y="32" width="12" height="4" fill="#93a0af"/>
<rect x="14" y="34" width="36" height="24" fill="#93a0af"/><rect x="16" y="36" width="32" height="20" fill="#fdfdfc"/>
<rect x="30" y="40" width="4" height="12" fill="#b23c2e"/><rect x="26" y="44" width="12" height="4" fill="#b23c2e"/>
</g>"""

HEART = ('<g transform="translate(%d,%d)" fill="%s"%s><rect x="2" y="0" width="4" height="2"/>'
         '<rect x="8" y="0" width="4" height="2"/><rect x="0" y="2" width="14" height="4"/>'
         '<rect x="2" y="6" width="10" height="2"/><rect x="4" y="8" width="6" height="2"/>'
         '<rect x="6" y="10" width="2" height="2"/></g>')

FONT = "-apple-system,'Segoe UI',Roboto,Helvetica,sans-serif"
MONO = "ui-monospace,Menlo,Consolas,monospace"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def hearts_svg(x, y, grade):
    n = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}.get((grade or " ")[0].upper(), 0)
    color = GRADE_COLOR.get((grade or " ")[0].upper(), PAL["ink3"])
    out = []
    for i in range(5):
        dim = "" if i < n else ' opacity="0.22"'
        out.append(HEART % (x + i * 18, y, color, dim))
    return "".join(out)


def fallback_note(grade, verdict_counts, criticals, warns):
    g = (grade or " ")[0].upper()
    if verdict_counts.get("ignored"):
        return "The loudest rule was the broken one."
    if g == "A":
        return "Clean bill of health. Stay boring."
    if criticals:
        return "The chart no longer matches the patient."
    if warns:
        return "Mostly healthy. The numbers rotted first."
    return "Examined. Nothing to report — which is a report."


def wrap(text, width=52, max_lines=2):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;") + "…"
    return lines


def build_card(name, grade, note, stats, class_counts):
    gcol = GRADE_COLOR.get((grade or " ")[0].upper(), PAL["ink3"])
    note_lines = wrap(note)
    note_svg = "".join(
        '<text x="60" y="%d" font-size="26" font-weight="600" fill="%s" '
        'font-family="%s">%s</text>'
        % (196 + i * 36, PAL["ink"], FONT, esc(l))
        for i, l in enumerate(note_lines))
    # class-distribution mini bar (aggregate-safe)
    total = sum(class_counts.values()) or 1
    bar, bx = [], 60
    for cls in ("hook", "linter", "test", "judge", "unclassified"):
        n = class_counts.get(cls, 0)
        if not n:
            continue
        w = max(int(340.0 * n / total), 6)
        bar.append('<rect x="%d" y="330" width="%d" height="12" fill="%s"/>'
                   % (bx, w, CLASS_COLOR[cls]))
        bx += w
    legend = " · ".join("%s %d" % (c, n) for c, n in class_counts.items() if n)
    stat_rows = "".join(
        '<text x="60" y="%d" font-size="14" fill="%s" font-family="%s">%s</text>'
        % (268 + i * 22, PAL["ink2"], FONT, esc(s))
        for i, s in enumerate(stats))
    title = ('<text x="128" y="88" font-size="26" font-weight="700" fill="%s" '
             'font-family="%s">%s</text>' % (PAL["ink"], FONT, esc(name))
             if name else "")
    # viewBox only (no fixed width/height): scales to any viewer instead of
    # clipping in containers narrower than 800px
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 418">
<rect width="800" height="418" fill="%(bg)s"/>
<rect x="14" y="14" width="772" height="390" rx="16" fill="%(card)s" stroke="%(line)s"/>
%(bot)s
<text x="128" y="60" font-size="12" letter-spacing="2.5" fill="%(ink2)s" font-family="%(mono)s">CLAUDE-MD-DOCTOR · CHECKUP</text>
%(title)s
<rect x="648" y="40" width="104" height="66" rx="3" fill="%(card)s" stroke="%(gcol)s" stroke-width="3"/>
<rect x="654" y="110" width="104" height="4" fill="%(line)s"/>
<text x="700" y="78" font-size="34" font-weight="700" fill="%(gcol)s" text-anchor="middle" font-family="%(mono)s">%(grade)s</text>
%(hearts)s
<path d="M46 140 H210 V134 H214 V140 H250 V144 H254 V140 H420 V132 H424 V145 H428 V140 H580 V134 H584 V140 H620 V144 H624 V140 H754" fill="none" stroke="%(accent)s" stroke-width="2" shape-rendering="crispEdges"/>
%(note)s
%(stats)s
%(bar)s
<text x="60" y="358" font-size="11" fill="%(ink3)s" font-family="%(font)s">%(legend)s</text>
<text x="60" y="386" font-size="13" fill="%(ink2)s" font-family="%(font)s">give your CLAUDE.md a checkup</text>
<text x="740" y="386" font-size="12" text-anchor="end" fill="%(ink3)s" font-family="%(mono)s">npx skills add agent-clinic/claude-md-doctor</text>
</svg>""" % {"bg": PAL["bg"], "card": PAL["card"], "line": PAL["line"],
             "ink2": PAL["ink2"], "ink3": PAL["ink3"], "accent": PAL["accent"],
             "mono": MONO, "font": FONT, "gcol": gcol, "grade": esc(grade),
             "bot": BOT % (44, 40, "1.05"), "title": title,
             "hearts": hearts_svg(656, 88, grade), "note": note_svg,
             "stats": stat_rows, "bar": "".join(bar), "legend": esc(legend)}


def build_badge(grade):
    gcol = GRADE_COLOR.get((grade or " ")[0].upper(), PAL["ink3"])
    label, value = "CLAUDE.md checkup", "grade %s" % grade
    lw, vw = 10 + len(label) * 7, 10 + len(value) * 7
    return """<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="20" role="img" aria-label="%s: %s">
<clipPath id="r"><rect width="%d" height="20" rx="3"/></clipPath>
<g clip-path="url(#r)">
<rect width="%d" height="20" fill="#555"/>
<rect x="%d" width="%d" height="20" fill="%s"/>
</g>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
<text x="%d" y="14">%s</text>
<text x="%d" y="14" font-weight="bold">%s</text>
</g>
</svg>""" % (lw + vw, esc(label), esc(value), lw + vw, lw, lw, vw, gcol,
             lw // 2, esc(label), lw + vw // 2, esc(value))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--name", default=None,
                    help="display name on the card (default: repo basename)")
    ap.add_argument("--anonymous", action="store_true",
                    help="omit the repo name entirely")
    args = ap.parse_args()
    work = args.work
    intake = load_json(os.path.join(work, "intake.json")) or {}
    vitals = load_json(os.path.join(work, "vitals.json")) or {}
    backtest = load_json(os.path.join(work, "backtest.json")) or {}
    rulebook = load_json(os.path.join(work, "rulebook.json")) or {}
    diagnosis = load_json(os.path.join(work, "diagnosis.json")) or {}

    grade = diagnosis.get("grade", "—")
    name = "" if args.anonymous else \
        (args.name or os.path.basename(intake.get("repo", "")) or "")

    # aggregate-only stats — never a path, rule text, or repo quote
    combined = vitals.get("launch_loaded_combined", {})
    rules = rulebook.get("rules", [])
    class_counts, lawable, already = {}, 0, 0
    for r in rules:
        enf = r.get("enforcement") or {}
        cls = enf.get("class") or "unclassified"
        class_counts[cls] = class_counts.get(cls, 0) + 1
        if cls in ("hook", "linter", "test"):
            if (enf.get("current_layer") or "prose") == "prose":
                lawable += 1
            else:
                already += 1
    verdict_counts = {}
    for v in (diagnosis.get("rule_verdicts") or {}).values():
        verdict_counts[v.get("verdict", "?")] = \
            verdict_counts.get(v.get("verdict", "?"), 0) + 1
    criticals = len([d for d in diagnosis.get("diagnoses", [])
                     if d.get("severity") == "critical"])
    warns = len([d for d in diagnosis.get("diagnoses", [])
                 if d.get("severity") == "warn"])

    note = diagnosis.get("share_note") or fallback_note(
        grade, verdict_counts, criticals, warns)

    stats = []
    if combined:
        stats.append("%s effective lines · ~%s tokens loaded every session"
                     % ("{:,}".format(combined.get("effective_lines", 0)),
                        "{:,}".format(combined.get("est_tokens", 0))))
    if rules:
        stats.append("%d directives · %d could be laws · %d already are"
                     % (len(rules), lawable, already))
    sev_order = ("ignored", "abandoned", "mixed", "healthy", "inert", "unmeasured")
    vbits = [("%d %s" % (verdict_counts[k], k)) for k in sev_order
             if verdict_counts.get(k)]
    vbits += [("%d %s" % (n, k)) for k, n in verdict_counts.items()
              if n and k not in sev_order]
    if vbits:
        stats.append(" · ".join(vbits))

    out_dir = os.path.dirname(work)
    card_path = os.path.join(out_dir, "card.svg")
    badge_path = os.path.join(out_dir, "claude-md-health.svg")
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(build_card(name, grade, note, stats, class_counts))
    with open(badge_path, "w", encoding="utf-8") as f:
        f.write(build_badge(grade))
    manifest_add(work, "card", grade=grade)
    print("card: %s" % card_path)
    print("badge: %s" % badge_path)
    print("badge snippet: [![CLAUDE.md health](%s)]"
          "(https://github.com/agent-clinic/claude-md-doctor)"
          % os.path.basename(badge_path))


if __name__ == "__main__":
    main()

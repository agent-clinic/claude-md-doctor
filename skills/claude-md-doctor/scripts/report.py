#!/usr/bin/env python3
"""Stage 5 — report: assemble the doctor's report from the exam artifacts.

Reads intake/vitals/refcheck.json plus diagnosis.json (written by the model —
grade, diagnoses, prescriptions, stale-claim verdicts) and renders a single
self-contained HTML report plus a machine-readable report.json. Verifies the
work-state manifest: a skipped exam stage is disclosed, never papered over.

Usage: python3 report.py --work DIR [--out FILE]
"""

import argparse
import html
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_json, save_json, manifest_add

VERSION = "0.2.0"

HEART_RECTS = ('<rect x="2" y="0" width="4" height="2"/><rect x="8" y="0" width="4" height="2"/>'
               '<rect x="0" y="2" width="14" height="4"/><rect x="2" y="6" width="10" height="2"/>'
               '<rect x="4" y="8" width="6" height="2"/><rect x="6" y="10" width="2" height="2"/>')


def build_hearts(grade):
    """Condition meter: pixel hearts filled by grade (A=5 … F=1)."""
    n = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}.get((grade or " ")[0].upper(), 0)
    out = []
    for i in range(5):
        style = "" if i < n else ";opacity:.22"
        out.append('<svg width="13" height="12" viewBox="0 0 14 12" '
                   'shape-rendering="crispEdges" style="margin:0 1px%s">'
                   '<g fill="currentColor">%s</g></svg>' % (style, HEART_RECTS))
    return "".join(out)
REQUIRED_STAGES = ("intake", "vitals", "refcheck", "diagnosis")

CITATIONS = {
    "official-200": ("Claude Code memory doc — “Size: target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence.”", "https://code.claude.com/docs/en/memory"),
    "official-best-practices": ("Claude Code best practices — deletion test; “Bloated CLAUDE.md files cause Claude to ignore your actual instructions!”; sparse emphasis.", "https://code.claude.com/docs/en/best-practices"),
    "official-hooks": ("Claude Code memory doc — CLAUDE.md is “context, not enforced configuration”; use a PreToolUse hook to block an action regardless.", "https://code.claude.com/docs/en/memory"),
    "official-4mib": ("Claude Code memory doc — a CLAUDE.md over 4 MiB is skipped entirely.", "https://code.claude.com/docs/en/memory"),
    "official-40k": ("Claude Code troubleshooting — startup warning at 40,000 characters of memory content.", "https://code.claude.com/docs/en/troubleshooting"),
    "eth": ("Gloaguen et al. (ETH Zurich), “Evaluating AGENTS.md” (v2): context files cost +20–23% inference with no significant success change; agents measurably comply with explicit directives; “describe only minimal requirements.”", "https://arxiv.org/abs/2602.11988"),
    "mcmillan": ("McMillan, factorial study of 1,650 Claude Code sessions: no detectable structural effect of file size/position/contradictions in tested range; within-session adherence decay ≈ 5.6%/function.", "https://arxiv.org/abs/2605.10039"),
    "ifscale": ("IFScale: adherence 98.4% at 100 instructions → 84.8% at 250 → 68.9% at 500; errors shift to silent omission.", "https://arxiv.org/abs/2507.11538"),
    "agentif": ("AGENTIF (NeurIPS 2025): best model satisfies all constraints of an agentic instruction 27.2% of the time; ≈0 past 6,000 words.", "https://arxiv.org/abs/2505.16944"),
    "sysbench": ("SysBench: system-message constraint adherence decays ≈12.8pp/turn over 5 turns (GPT-4o).", "https://arxiv.org/abs/2408.10943"),
    "levy": ("Levy, Jacoby & Goldberg (ACL 2024): accuracy 0.92 → 0.68 with 3,000 tokens of padding; degradation starts ≈500 tokens.", "https://arxiv.org/abs/2402.14848"),
    "chroma": ("Chroma “Context Rot”: 18 models degrade with input length even on trivial tasks; focused ~300-token prompts beat 113k-token contexts.", "https://www.trychroma.com/research/context-rot"),
    "longllmlingua": ("LongLLMLingua (ACL 2024): +21.4% at ~4× prompt compression — cutting filler can raise performance.", "https://arxiv.org/abs/2310.06839"),
    "caps": ("Dillitzer et al., “Attention is Case-Sensitive”: uppercase shifts +1.85pp accuracy; near-zero on reasoning models; saturation spends the effect.", "https://arxiv.org/abs/2608.03711"),
    "sigil": ("SIGIL: prose agents perform 56% of the steps their own skill mandates while outputs still pass checks; script-compiled harnesses reach 86%.", "https://arxiv.org/abs/2607.27309"),
    "agent-readmes": ("“Agent READMEs” (2,303 context files): tests 75.9% / implementation 70.8% / architecture 68.1%; security & performance nearly absent; files accrete without pruning.", "https://arxiv.org/abs/2511.12884"),
    "cursor-rules": ("Jiang & Nam (MSR 2026), 401 repos: five-theme content taxonomy; ~28.7% duplicated lines across a repo's rules files.", "https://arxiv.org/abs/2512.18925"),
    "awm": ("Agent Workflow Memory: induced, selectively-loaded workflows +51.1% relative on WebArena — recurring procedures belong in on-demand skills.", "https://arxiv.org/abs/2409.07429"),
    "unblocked": ("Unblocked, “Audit a bloated CLAUDE.md in 7 steps” — the manual audit this tool automates.", "https://getunblocked.com/blog/audit-fix-bloated-claude-md/"),
    "surface-bloat": ("“Too Many CLAUDE.md and Skill Files?” — aggregate memory surfaces fail silently (60 files ≈ 64k standing tokens); fixes: consolidate → thin router/index → one-screen invariants + on-demand procedures.", "https://xtrace.ai/blog/too-many-claude-skill-files"),
}

SEV_PILL = {"critical": "p-crit", "warn": "p-warn", "info": "p-info", "ok": "p-ok"}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def cite(ids, order):
    sups = []
    for cid in ids or []:
        if cid not in CITATIONS:
            continue
        if cid not in order:
            order.append(cid)
        sups.append('<sup><a href="#fn-%s">[%d]</a></sup>' % (cid, order.index(cid) + 1))
    return "".join(sups)


def build_patient(intake, vitals):
    rows = []
    def row(k, v):
        rows.append("<tr><th style='width:220px'>%s</th><td>%s</td></tr>" % (k, v))
    row("Repository", "<code>%s</code>" % esc(intake["repo"]))
    files = [f for f in intake["files"] if f["exists"] and not f["excluded"]]
    internal = [f for f in files if not f["external"]]
    row("Files examined", "%d in-repo (%d launch-loaded), %d external noted"
        % (len(internal), len(intake["effective_launch_loaded"]),
           len(files) - len(internal)))
    pointers = [f for f in files if f.get("is_pointer")]
    if pointers:
        row("Pointer pattern", "CLAUDE.md points at %s (healthy pattern; the target was examined)"
            % ", ".join("<code>%s</code>" % esc(os.path.basename(t))
                        for f in pointers for t in f["pointer_targets"]))
    excl = [f for f in intake["files"] if f["excluded"]]
    if excl:
        row("Excluded via claudeMdExcludes", ", ".join("<code>%s</code>" % esc(f["rel"] or f["path"]) for f in excl))
    us = intake.get("user_scope", {})
    row("User-scope memory", ("~/.claude/CLAUDE.md %s, %d user rules — %s"
        % ("present" if us.get("user_claude_md_exists") else "absent",
           us.get("user_rules_count", 0),
           "included in exam" if us.get("included_in_exam") else "not examined (repo scope only)")))
    sess = intake.get("sessions", {})
    row("Session history found", ("%d transcript(s) at <code>%s</code> — not examined in v0.1"
        % (sess.get("session_files", 0), esc(sess.get("dir"))))
        if sess.get("dir") else "none found for this path on this machine")
    return "\n".join(rows)


def build_vitals(vitals, order):
    c = vitals["launch_loaded_combined"]
    t = vitals["thresholds"]
    biggest = max(vitals["per_file"].items(),
                  key=lambda kv: kv[1]["effective_lines"], default=(None, None))
    cards = []
    def card(v, k, note, cls=""):
        cards.append('<div class="card %s"><div class="v">%s</div>'
                     '<div class="k">%s</div><div class="n">%s</div></div>'
                     % (cls, v, k, note))
    if biggest[0]:
        b = biggest[1]
        over = b["effective_lines"] > t["size_target_lines"]
        card(b["effective_lines"],
             "lines — %s" % esc(os.path.basename(biggest[0])),
             "official target: under %d%s" % (t["size_target_lines"],
                                              cite(["official-200"], order)),
             "bad" if over else "fine")
    card("%s" % c["est_tokens"], "est. tokens loaded every session",
         "%.2f%% of a %dk context (estimate)" % (c["pct_of_context"],
                                                 t["context_budget_tokens"] // 1000),
         "warned" if c["est_tokens"] > 3000 else "fine")
    card("%d" % c["effective_lines"], "launch-loaded lines (all files)",
         "startup warning at %d chars: %s%s" % (t["startup_warn_chars"],
             "TRIGGERED" if c["startup_warning"] else "not triggered",
             cite(["official-40k"], order)),
         "bad" if c["startup_warning"] else "fine")
    return "\n".join(cards)


def build_files_table(vitals):
    rows = []
    for path, m in sorted(vitals["per_file"].items(),
                          key=lambda kv: -kv[1]["effective_lines"]):
        if m["external"] and m["scope"] != "ancestor":
            continue
        markers = []
        if m["is_pointer"]:
            markers.append('<span class="pill p-ok">pointer</span>')
        if m["over_size_target"]:
            markers.append('<span class="pill p-crit">over 200</span>')
        if m["init_boilerplate"]:
            markers.append('<span class="pill p-warn">/init boilerplate</span>')
        if m["emphasis_per_100_lines"] > 15:
            markers.append('<span class="pill p-warn">emphasis %s/100</span>'
                           % m["emphasis_per_100_lines"])
        if m["dated_per_100_lines"] > 10:
            markers.append('<span class="pill p-warn">dated entries</span>')
        if m["scope"] == "ancestor":
            markers.append('<span class="pill p-info">ancestor</span>')
        if m["comment_lines_removed"]:
            markers.append('<span class="pill p-info">%d comment lines free</span>'
                           % m["comment_lines_removed"])
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>"
                    % (esc(os.path.basename(path) if m["scope"] != "nested"
                           else path), m["effective_lines"], m["est_tokens"],
                       " ".join(markers) or "—"))
    return "\n".join(rows)


def build_lab(refcheck, diagnosis, order):
    if not refcheck:
        return "<div class='note'>Records check did not run.</div>"
    parts = []
    flagged = [r for r in refcheck["references"]
               if r["status"] in ("missing", "machine_specific", "glob_empty")]
    dismissed = {d["ref"]: d.get("reason", "reviewed: not a real reference")
                 for d in (diagnosis or {}).get("dismissed_refs", [])}
    bad_refs = [r for r in flagged if r["ref"] not in dismissed]
    dropped = [r for r in flagged if r["ref"] in dismissed]
    ok_n = len(refcheck["references"]) - len(flagged)
    parts.append("<p class='sub'>%d path references checked — %d resolve, "
                 "%d flagged (%d confirmed on review, %d dismissed as false "
                 "positives). %d commands checked — %d missing.</p>"
                 % (len(refcheck["references"]), ok_n, len(flagged),
                    len(bad_refs), len(dropped), len(refcheck["commands"]),
                    refcheck["stats"]["commands_missing"]))
    if bad_refs:
        rows = ["<tr><th>Reference</th><th>Where</th><th>Status</th><th>Detail</th></tr>"]
        for r in bad_refs:
            pill = {"missing": "p-crit", "machine_specific": "p-crit",
                    "glob_empty": "p-warn"}[r["status"]]
            rows.append("<tr><td><code>%s</code></td><td class='mono'>%s:%s</td>"
                        "<td><span class='pill %s'>%s</span></td><td>%s</td></tr>"
                        % (esc(r["ref"]), esc(os.path.basename(r["file"])),
                           r["line"], pill, r["status"].replace("_", " "),
                           esc(r["detail"])))
        parts.append("<div class='tablebox'><table>%s</table></div>" % "".join(rows))
    if dropped:
        items = "".join("<li><code>%s</code> — %s</li>"
                        % (esc(r["ref"]), esc(dismissed[r["ref"]]))
                        for r in dropped)
        parts.append("<details><summary>%d flag(s) dismissed on review</summary>"
                     "<ul class='plain foot'>%s</ul></details>"
                     % (len(dropped), items))
    missing_cmds = [c for c in refcheck["commands"] if c["status"] == "missing"]
    if missing_cmds:
        rows = ["<tr><th>Command</th><th>Where</th><th>Detail</th></tr>"]
        for c in missing_cmds:
            rows.append("<tr><td><code>%s</code></td><td class='mono'>%s:%s</td><td>%s</td></tr>"
                        % (esc(c["command"]), esc(os.path.basename(c["file"])),
                           c["line"], esc(c["detail"])))
        parts.append("<div style='height:10px'></div><div class='tablebox'><table>%s</table></div>" % "".join(rows))
    for rs in refcheck.get("rule_scopes", []):
        if rs["status"] == "dead_scope":
            parts.append("<div class='note'>Rules file <code>%s</code> has a <code>paths:</code> scope matching zero files — it never loads.</div>"
                         % esc(os.path.basename(rs["file"])))
    claims = (diagnosis or {}).get("stale_claims", [])
    if claims:
        rows = ["<tr><th>Claim in file</th><th>Where</th><th>Verdict</th><th>Detail</th></tr>"]
        for cl in claims:
            pill = {"verified": "p-ok", "drifted": "p-crit",
                    "unverified": "p-info"}.get(cl["status"], "p-info")
            rows.append("<tr><td>%s</td><td class='mono'>%s:%s</td>"
                        "<td><span class='pill %s'>%s</span></td><td>%s</td></tr>"
                        % (esc(cl["claim"]), esc(os.path.basename(cl.get("file", ""))),
                           cl.get("line", ""), pill, cl["status"], esc(cl.get("detail", ""))))
        parts.append("<h2 style='margin-top:22px'>Checkable claims</h2><div class='tablebox'><table>%s</table></div>" % "".join(rows))
    return "\n".join(parts)


VERDICT_PILL = {"healthy": "p-ok", "ignored": "p-crit", "mixed": "p-warn",
                "inert": "p-info", "unverified": "p-info"}


def build_history(backtest, diagnosis, order, fallback_note):
    if not backtest:
        return "<p class='sub'>%s</p>" % esc(fallback_note)
    w = backtest.get("window", {})
    parts = []
    if not backtest.get("verified"):
        parts.append("<div class='note'>Backtest ran but its samples were not "
                     "verified — matcher results below are provisional.</div>")
    parts.append(
        "<p class='sub'>Replayed every rule over <b>%s session(s)</b> — %s tool "
        "calls, %s → %s (%s stub sessions skipped). %s.%s</p>"
        % (w.get("sessions_replayed", 0), w.get("total_tool_calls", 0),
           esc((w.get("from") or "")[:10]), esc((w.get("to") or "")[:10]),
           w.get("stub_sessions_skipped", 0),
           esc(w.get("machine_note", "")), cite(["mcmillan", "sysbench"], order)))
    verdicts = (diagnosis or {}).get("rule_verdicts", {})
    rows = ["<tr><th>Rule</th><th>Opportunities</th><th>Compliance</th>"
            "<th>Violations</th><th>Verdict</th></tr>"]
    depth_totals = {"early": 0, "mid": 0, "late": 0}
    for rid, st in (backtest.get("per_rule") or {}).items():
        for k in depth_totals:
            depth_totals[k] += st["violations_by_depth"].get(k, 0)
        v = verdicts.get(rid, {})
        verdict = v.get("verdict") or (
            "inert" if st["opportunities"] == 0 else
            "healthy" if st["violations"] == 0 else
            "ignored" if st["compliances"] == 0 else "mixed")
        decided = st["compliances"] + st["violations"]
        comp = ("%d%%" % round(100.0 * st["compliances"] / decided)) if decided else "—"
        ev = ""
        samples = st["samples"]["violations"] + st["samples"]["compliances"]
        if samples or v.get("note"):
            lines = ([v["note"]] if v.get("note") else []) + [
                "%s (turn %s): %s" % (s.get("session", "")[:8],
                                      s.get("turn", "?"),
                                      s.get("excerpt") or s.get("note", ""))
                for s in samples]
            ev = ("<details><summary>evidence</summary><pre>%s</pre></details>"
                  % esc("\n".join(lines)))
        rows.append(
            "<tr><td><span class='mono'>%s</span> %s%s</td><td>%d</td><td>%s</td>"
            "<td>%d</td><td><span class='pill %s'>%s</span></td></tr>"
            % (esc(rid), esc(st["text"][:90]), ev, st["opportunities"], comp,
               st["violations"], VERDICT_PILL.get(verdict, "p-info"),
               esc(verdict)))
    parts.append("<div class='tablebox'><table>%s</table></div>" % "".join(rows))
    total_v = sum(depth_totals.values())
    if total_v:
        parts.append("<p class='sub'>Violations by conversation depth: "
                     "%d early (≤3 turns) · %d mid (4–8) · %d late (>8)%s.</p>"
                     % (depth_totals["early"], depth_totals["mid"],
                        depth_totals["late"], cite(["sysbench"], order)))
    return "\n".join(parts)


def build_diagnoses(diagnosis, order):
    out = []
    for d in (diagnosis or {}).get("diagnoses", []):
        loc = ""
        if d.get("file"):
            loc = "<span class='dx-loc'>%s%s</span>" % (
                esc(os.path.basename(d["file"])),
                ":%s" % d["line"] if d.get("line") else "")
        ev = ""
        if d.get("evidence"):
            ev = ("<details><summary>evidence</summary><pre>%s</pre></details>"
                  % esc("\n".join(d["evidence"])))
        rx = ""
        if d.get("prescription"):
            rx = "<div class='rx'><b>💊 Prescription</b>%s</div>" % esc(d["prescription"])
        out.append(
            "<div class='dx'><div class='dx-head'>"
            "<span class='pill %s'>%s</span>"
            "<span class='pill p-info'>%s</span>"
            "<span class='dx-title'>%s</span>%s%s</div>"
            "<p>%s</p>%s%s</div>"
            % (SEV_PILL.get(d.get("severity", "info"), "p-info"),
               esc(d.get("severity", "info")), esc(d.get("state", "")),
               esc(d.get("title", "")), loc, cite(d.get("citations"), order),
               esc(d.get("detail", "")), ev, rx))
    return "\n".join(out) or "<p class='sub'>No diagnoses recorded.</p>"


RX_EMOJIS = ["💊", "🩹", "💉", "🧪", "🌡️"]


def build_prescriptions(diagnosis, order):
    items = []
    for i, p in enumerate((diagnosis or {}).get("prescriptions", [])):
        items.append("<li><span class='pe'>%s</span><div><b>%s</b>%s<br>"
                     "<span class='sub'>%s</span></div></li>"
                     % (RX_EMOJIS[i % len(RX_EMOJIS)], esc(p.get("action", "")),
                        cite(p.get("citations"), order),
                        esc(p.get("rationale", ""))))
    return "<ul class='rxlist'>%s</ul>" % "".join(items) if items \
        else "<p class='sub'>None beyond the per-diagnosis prescriptions.</p>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    work = args.work
    intake = load_json(os.path.join(work, "intake.json"))
    vitals = load_json(os.path.join(work, "vitals.json"))
    refcheck = load_json(os.path.join(work, "refcheck.json"))
    diagnosis = load_json(os.path.join(work, "diagnosis.json"))
    manifest = load_json(os.path.join(work, "manifest.json"), {"stages": []})
    if not (intake and vitals):
        sys.exit("report: intake.json and vitals.json are required")

    done = {s["stage"] for s in manifest["stages"]}
    if diagnosis:
        done.add("diagnosis")
    missing = [s for s in REQUIRED_STAGES if s not in done]
    exam_note = ""
    if missing:
        exam_note = ("<div class='note'>Incomplete exam: stage(s) %s did not run. "
                     "Findings below cover only the completed stages.</div>"
                     % esc(", ".join(missing)))

    order = []
    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "templates", "report.html")
    tpl = open(tpl_path, encoding="utf-8").read()
    backtest = load_json(os.path.join(work, "backtest.json"))
    grade = (diagnosis or {}).get("grade", "—")
    history_fallback = (diagnosis or {}).get("history_note") or (
        "Not examined in this run. %d session transcript(s) were located for "
        "this repo — the backtest replays each rule against them."
        % intake.get("sessions", {}).get("session_files", 0))
    followup = "".join("<li><span class='pe'>🩺</span><div>%s</div></li>" % esc(f)
                       for f in (diagnosis or {}).get("followup", []))

    repl = {
        "{{REPO_NAME}}": esc(os.path.basename(intake["repo"])),
        "{{EXAM_DATE}}": time.strftime("%Y-%m-%d %H:%M"),
        "{{VERSION}}": VERSION,
        "{{GRADE}}": esc(grade),
        "{{HEARTS}}": build_hearts(grade),
        "{{GRADE_CLASS}}": (grade[:1].lower() if grade and grade[0].isalpha() else "c"),
        "{{CHIEF_COMPLAINT}}": esc((diagnosis or {}).get(
            "chief_complaint", "No model diagnosis pass was recorded.")),
        "{{EXAM_NOTE}}": exam_note,
        "{{PATIENT_ROWS}}": build_patient(intake, vitals),
        "{{VITALS_CARDS}}": build_vitals(vitals, order),
        "{{FILES_TABLE}}": build_files_table(vitals),
        "{{LAB_HTML}}": build_lab(refcheck, diagnosis, order),
        "{{HISTORY_HTML}}": build_history(backtest, diagnosis, order,
                                          history_fallback),
        "{{DIAGNOSES_HTML}}": build_diagnoses(diagnosis, order),
        "{{PRESCRIPTIONS_HTML}}": build_prescriptions(diagnosis, order),
        "{{FOLLOWUP_HTML}}": "<ul class='rxlist'>%s</ul>" % (
            followup or "<li><span class='pe'>🩺</span>"
            "<div>Re-run after applying prescriptions.</div></li>"),
    }
    footnotes = "".join(
        '<li id="fn-%s">%s <a href="%s">%s</a></li>'
        % (cid, esc(CITATIONS[cid][0]), esc(CITATIONS[cid][1]),
           esc(CITATIONS[cid][1])) for cid in order)
    repl["{{FOOTNOTES_HTML}}"] = footnotes or "<li>No citations referenced.</li>"

    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    out_path = args.out or os.path.join(os.path.dirname(work), "report.html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(tpl)

    save_json(os.path.join(os.path.dirname(work), "report.json"),
              {"version": VERSION, "repo": intake["repo"],
               "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "grade": grade, "vitals": vitals, "refcheck_stats":
               (refcheck or {}).get("stats"), "diagnosis": diagnosis,
               "backtest": backtest, "incomplete_stages": missing})
    manifest_add(work, "report", out=out_path, incomplete=missing)
    print("report: wrote %s%s" % (out_path,
          " (INCOMPLETE: missing %s)" % ",".join(missing) if missing else ""))


if __name__ == "__main__":
    main()

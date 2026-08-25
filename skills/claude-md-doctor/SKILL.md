---
name: claude-md-doctor
description: Give this repo's CLAUDE.md / AGENTS.md a checkup — size vitals vs official guidance, dead file references, dead commands, stale claims, pathology markers — and produce a doctor-style HTML report with evidence-cited prescriptions. Use when asked to check, diagnose, audit, lint, or "doctor" CLAUDE.md, AGENTS.md, or agent instruction/memory files.
argument-hint: "[repo path] [--include-user]"
---

# CLAUDE.md Doctor — exam procedure (v0.2: static exam + session backtest)

You are running a checkup on this repository's agent-instruction files. The
deterministic work lives in scripts; your job is the judgment between them.
Do not re-derive what a script already measured, and do not skip a stage — the
report verifies the work-state manifest and will disclose skipped stages.

Definitions used below:
- `SKILL_DIR` = the directory containing this SKILL.md.
- `SCRIPTS` = `SKILL_DIR/scripts`.
- `REPO` = the repository to examine (the argument if one was given, else the
  current working directory).
- `WORK` = `REPO/.claude-md-doctor/work` (scripts default to this; pass
  `--work` to relocate, e.g. into a scratch directory to avoid writing in the
  user's repo — prefer that when the repo is not yours to dirty).

## Stage 0 — preflight

Run `python3 --version`. If python3 is missing, stop and tell the user this
skill needs Python 3.9+ (stdlib only, nothing to install).

## Stage 1 — intake

    python3 SCRIPTS/intake.py --repo REPO --work WORK

Then read `WORK/intake.json` (it is small). Note for later judgment:
- Is the project CLAUDE.md a **pointer** (`is_pointer`) to AGENTS.md? That is
  the healthy, officially-recommended pattern — the target is the patient.
  Never diagnose a pointer file as "too short." Check `pointer_style`:
  `symlink` and `import` work; **`bare-text` is a broken pointer** — a regular
  file containing just `AGENTS.md` without `@` means Claude Code never loads
  the target. That is a critical diagnosis with a one-character fix (`@`),
  unless you are examining a raw-fetched copy where symlinks flatten to text.
- Ancestor and user-scope files are context the session loads but the repo
  can't fix — mention them, don't prescribe changes to them unless asked.
- If NO memory files exist at all, stop and report that: the prescription is
  to create one (suggest `/init` then aggressive pruning), not an empty report.

## Stage 2 — vitals

    python3 SCRIPTS/vitals.py --work WORK

Read `WORK/vitals.json`. The script measured; you interpret. Detector notes:
- `init_boilerplate` means the file still opens with stock `/init` output — a
  generated-and-never-pruned marker.
- `emphasis_per_100_lines` matters as **density**, not presence (sparse
  emphasis is officially endorsed).
- High `dated_per_100_lines` suggests session-log/changelog accretion.
- Very low `imperative_ratio` on a large file suggests narrative documentation
  rather than instructions — read a sample and judge; the arcan case (a
  CLAUDE.md containing a sabotage manual) is why this check exists.
- **Judge the aggregate surface, not only each file** (`launch_loaded_combined`
  plus the file count): many individually-healthy files can still sum to a
  heavy standing context, and cross-file duplication or contradiction is
  invisible per-file. When the combined surface is the problem, prescribe the
  escalating ladder — consolidate duplicates, then a thin router/index over
  on-demand files, then a one-screen always-on invariants file with
  procedures moved to skills (citation id `surface-bloat`).

## Stage 3 — records check

    python3 SCRIPTS/refcheck.py --work WORK

Read `WORK/refcheck.json`. Your judgment passes:
1. **Review the failures, don't parrot them.** For each `missing` /
   `machine_specific` / `glob_empty` reference and each `missing` command,
   open the cited file:line and confirm it is a real reference (not prose that
   merely looks like a path — API endpoints, MIME types, git refs, and files
   the text describes as deleted are the common false positives). Record each
   false positive in `dismissed_refs` with its reason: the report shows only
   confirmed findings and discloses dismissals in a collapsed note.
2. **Extract checkable claims** the scripts cannot: countable assertions in
   the memory files ("3,540 tests across 374 files", "12 UI components",
   "there is no ESLint config"). Verify the cheap ones with quick commands
   (file counts, grep for configs). Do NOT run test suites or builds unless
   the user asked. Record each as `verified` / `drifted` / `unverified` with a
   one-line detail — `unverified` is an honest answer for anything expensive.

## Stage 4 — history backtest

Skip this stage only if intake found no session directory (`sessions.dir`
null) — and then say so in chat; the report's History section will state it.

### 4a — condense the transcripts

    python3 SCRIPTS/sessions.py --work WORK

### 4b — decompose the memory files into a rulebook (your judgment)

Write `WORK/rulebook.json` (schema documented at the top of `backtest.py`).
Guidance:
- Only **mechanically checkable** rules get matchers in this version: bans and
  requirements visible in Bash commands or Edit/Write content ("never import
  X", "never hardcode a colour", "don't add an ESLint config"), and
  finish-ordering rules ("run `pnpm verify` before you finish") via
  `ordering`. Semantic rules ("keep components small in spirit") are judged in
  diagnoses, not matchers — do not force a regex onto them.
- For edit/write events the matchable text is `PATH: <file_path>` on the first
  line followed by the (truncated) new content — anchor path-based rules on
  `^PATH: .*…` and content rules on the body.
- Write **conservative** regexes (prefer false negatives over false
  positives), use `scope.paths` / `scope.exclude_paths` to confine
  file-scoped rules, and date each rule with `introduced` from
  `git log --follow --format=%aI -- <file>` when the file's history makes
  that cheap — sessions that ended before a rule existed must not count
  against adherence.

### 4c — run the engine

    python3 SCRIPTS/backtest.py --work WORK

### 4d — sample-verify (MANDATORY — matchers have bugs)

Read `WORK/backtest.json`. For EVERY rule with fires, read its sample
excerpts and confirm each is a true positive. A matcher with any false
positive gets fixed in `rulebook.json` and the engine re-run — this loop is
cheap and it is the whole reason the results can be trusted. Only when every
sampled fire is confirmed, set `"verified": true` in `backtest.json`
(edit the file) — the report shows a "provisional" banner otherwise.
Then record per-rule verdicts in `diagnosis.json` under `rule_verdicts`:

```json
"rule_verdicts": {
  "R1": {"verdict": "healthy|ignored|mixed|inert", "note": "one line of judgment"}
}
```

`inert` (zero opportunities in the window) is a finding, not a failure —
say what it means: the rule cost context in every session and never came up.

## Stage 5 — diagnosis (your judgment, written to a file)

Write `WORK/diagnosis.json`:

```json
{
  "grade": "B",
  "chief_complaint": "One sentence, doctor-voice, the single biggest issue.",
  "history_note": "optional override for the History section",
  "stale_claims": [
    {"claim": "…", "file": "/abs/path", "line": 12,
     "status": "verified|drifted|unverified", "detail": "…"}
  ],
  "dismissed_refs": [
    {"ref": "the exact ref string from refcheck.json", "reason": "why it is a false positive (route not file, MIME type, described as deleted, …)"}
  ],
  "diagnoses": [
    {"state": "dead-ref|stale|vague|ignored|inert|redundant|contradictory|oversized|accretion|generated-unpruned",
     "severity": "critical|warn|info",
     "title": "short name", "detail": "1–3 sentences, plain language",
     "file": "/abs/path", "line": 46,
     "evidence": ["short quoted lines or metric readouts"],
     "citations": ["official-200"],
     "prescription": "the concrete fix, imperative voice"}
  ],
  "prescriptions": [
    {"action": "repo-wide action", "rationale": "why", "citations": ["eth"]}
  ],
  "followup": ["re-run cadence, cleanupPeriodDays advice, v0.2 backtest note"]
}
```

Rules for this stage:
- **Every diagnosis needs evidence** (a quoted line, a metric, a failed check)
  and, where one exists, a citation id. Valid ids are in `report.py`'s
  CITATIONS table — use only those. A check with no official or research
  backing is stated as a heuristic in its `detail`.
- **Severity honestly**: `critical` = the file lies to the agent (dead refs,
  drifted claims, contradictions) or content is being skipped (4 MiB);
  `warn` = costs context or reduces adherence (oversized, emphasis
  saturation, accretion); `info` = worth knowing.
- **Structure-only findings carry a caution**: the one factorial study found
  no structural effect in its tested range (citation id `mcmillan`) — do not
  present size/position folklore as causal fact. Content findings (dead refs,
  drift) need no such hedge.
- **Grade rubric**: A = no critical, ≤2 warns; B = no critical, some warns;
  C = 1–2 criticals or pervasive warns; D = several criticals; F = the file
  is actively misleading (mostly dead/drifted) or unloadable. A pointer-style
  CLAUDE.md with a healthy target grades on the target.
- Cannot-fix scopes (ancestor/user/managed files) may generate `info`
  diagnoses only.

## Stage 5 — report

    python3 SCRIPTS/report.py --work WORK

Open or send the resulting `report.html` to the user, and summarize in chat:
grade, chief complaint, the top 3 findings, and the single highest-value
prescription. Tell the user where the report lives. If report.py printed an
INCOMPLETE warning, say which stage was missing and why.

## Conduct

- Everything runs locally; never send file contents anywhere.
- Quote at most ~2 lines from any file in evidence.
- v0.1 does not read session transcripts. If the user asks for adherence
  checking, say that is the v0.2 backtest and it is not built yet.

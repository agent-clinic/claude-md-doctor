---
name: claude-md-doctor
description: Give this repo's CLAUDE.md / AGENTS.md a checkup — size vitals vs official guidance, dead references, dead commands, stale claims — then backtest every rule against the repo's own Claude Code session history to see which rules were actually followed, ignored, or never used, and produce a doctor-style HTML report with evidence-cited prescriptions. Use when asked to check, diagnose, audit, review, improve, optimize, lint, grade, fix, clean up, shorten, or "doctor" CLAUDE.md, AGENTS.md, or agent instruction/memory files, or to find out whether CLAUDE.md rules actually work. Also use when a repo has NO memory file and the user wants one — "write/generate/suggest a CLAUDE.md (or hooks) from my sessions" — the skill mines the repo's real session history and drafts a proposed file with receipts.
argument-hint: "[repo path] [--include-user]"
---

# CLAUDE.md Doctor — exam procedure

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
- A file with scope `orphan-agents` means the repo has an AGENTS.md but no
  CLAUDE.md pointing at it — **Claude Code loads nothing**. That is a critical
  diagnosis with the official one-line fix (create a CLAUDE.md containing
  `@AGENTS.md`), and you should still run the full static exam on the
  AGENTS.md itself, since it becomes the patient the moment the pointer
  exists.
- If NO memory files exist at all, do not stop with an empty report — switch
  to **Mode B** (below): mine the session history and write the initial
  chart. Only when there is no session history either does the exam end,
  with the `/init`-plus-aggressive-pruning prescription and a note saying
  why nothing else could run.

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
- **Decompose EVERY directive in the file** — the rulebook is the complete
  directive inventory, and the enforcement ladder's "N of M" is only honest
  if M is the whole file. Only **mechanically checkable** rules get matchers:
  bans and requirements visible in Bash commands or Edit/Write content, and
  finish-ordering rules via `ordering`. Judge-class and not-yet-mechanizable
  rules go in as **classification-only entries** (enforcement block, no
  matchers) — never force a regex onto a semantic rule. Informational
  content (facts, architecture, API semantics) stays OUT of the rulebook.
- For edit/write events the matchable text is `PATH: <file_path>` on the first
  line followed by the (truncated) new content — anchor path-based rules on
  `^PATH: .*…` and content rules on the body.
- Write **conservative** regexes (prefer false negatives over false
  positives), use `scope.paths` / `scope.exclude_paths` to confine
  file-scoped rules, and date each rule with `introduced` from
  `git log --follow --format=%aI -- <file>` when the file's history makes
  that cheap — sessions that ended before a rule existed must not count
  against adherence.
- **Classify every rule's enforcement** (the `enforcement` block — schema at
  the top of `backtest.py`). Split compound rules into clauses first; each
  clause classifies independently. The class is the cheapest reliable
  detector: `hook` (event-stream regex: bash/edit/path/tool-input/output
  gates, ordering, cadence — try the event-ordering and standing-invariant
  reframings BEFORE surrendering a rule to judge), `linter`/`test` (static
  analysis over artifacts: lint rules, discipline tests, import-graph
  boundaries — record `scope_kind: file|project`), or `judge` (only an LLM
  can score it). A rule even a judge couldn't score is not a rule — diagnose
  it `vague`. Detect **existing enforcement**: if the repo already has the
  test/lint/hook the prose describes, set `current_layer` to it — that rule
  is a healthy pointer, never a prescription target. `current_layer` may also
  be an **org-level rule platform** (team-wide rulebooks with centralized
  detectors/telemetry) — the right home for cross-repo rules, judge-class
  auditing at scale, and staged warn→block rollouts that per-repo configs
  can't govern. Give every classified
  rule an `echo_regex` of its distinctive tokens (for proven-defiance
  detection) and an `origin` (root/nested/rules — only non-root rules can be
  truly absent after compaction). Also judge `against_prior: true|false` in
  the enforcement block: would a frontier model do this by default WITHOUT
  the rule? A with-prior rule showing high compliance may be coincidence,
  not obedience (citation id `harness-if`) — flag it as a redundancy
  candidate in diagnosis rather than celebrating it as healthy. And when
  prescribing move-to-skill: that move is for *procedures* only — a
  *constraint* demoted into a skill description measurably loses precedence
  (project files outrank tool/skill descriptions).

Engine semantics you need (so you don't reverse-engineer them):
- **"Opportunities"** = matcher fires (violation+compliance+context hits) for
  regex rules, and mutated-session count for ordering rules. Zero can mean
  "rule never applied" OR "your scope is wrong" — for any zero-fire
  path-scoped rule, run one **negative control** (confirm the sessions
  contain no events under that scope at all) before calling it inert.
- `scope.paths` filters only events that carry a file path; **bash events
  pass a paths filter** (they have no path) — for mixed bash+edit rules put
  path constraints into the regex (`^PATH: …`) if bash must be excluded.
- `exclude_paths` and `repo_only` DO apply to ordering-rule mutation
  counting.
- Edit/Write matchable content is **truncated to ~1200 chars** of new
  content (bash commands ~600) — first-line rules are fine; end-of-file or
  size rules are not expressible as content regexes.
- Condensed sessions are a **top-level JSON array** of event objects.
- **Read-before-edit ordering is NOT yet expressible** (`ordering.require`
  matches bash commands only) — classify such rules as unmechanized hooks;
  don't torture a regex.

### 4c — run the engine

    python3 SCRIPTS/backtest.py --work WORK

### 4d — sample-verify (MANDATORY — matchers have bugs)

Read `WORK/backtest.json`. For EVERY rule with fires — violation AND
compliance samples both — read the sample excerpts and confirm each is a
true positive. A matcher with any false
positive gets fixed in `rulebook.json` and the engine re-run — this loop is
cheap and it is the whole reason the results can be trusted. Only when every
sampled fire is confirmed, set `"verified": true` in `backtest.json`
(edit the file) — the report shows a "provisional" banner otherwise.

**Mention is not use.** The most common false positive is a session that
*talks about* a rule rather than breaking it: documenting the hazard,
grepping for offenders, writing the rule itself, quoting it in a commit
message or a retraction. A regex cannot tell discussion from violation, and
these land as `defiance-proven` — the most severe cause — because the rule
text is echoed right there. When a repo's own docs quote its rules, expect
this and check the excerpt for whether the event *performed* the banned
action or merely referred to it. Repos that document their own conventions
generate this heavily; drop those fires and tighten the matcher (anchor on
the action, exclude edits to the memory files and docs via
`scope.exclude_paths`).
Then record per-rule verdicts in `diagnosis.json` under `rule_verdicts`:

```json
"rule_verdicts": {
  "R1": {"verdict": "healthy|ignored|mixed|inert", "note": "one line of judgment"}
}
```

(That is the common subset — Stage 5's schema is canonical and adds
`unmeasured|abandoned|undocumented`; mined rules take `undocumented`.)

`inert` (zero opportunities in the window) is a finding, not a failure —
say what it means: the rule cost context in every session and never came up.

The engine also triages every violation by **cause**: `defiance-proven` (the
agent echoed the rule in its own text, then violated it — the reminder
already happened and lost), `defiance` (fresh context), `dilution` (late
turn / heavy context), `absence-risk` (non-root rule after a compaction
boundary). Read the causes before judging: they pick the medicine — proven
defiance justifies block-mode; dilution calls for slimming/path-scoping, not
cages; absence calls for re-injection hooks. Sanity-check the buckets while
sample-verifying (a "dilution" tag on a turn-2 violation means the occupancy
proxy misfired — say so). Ordering-rule caveat: verdicts are per-transcript —
in subagent/worktree workflows the required command may have run in a sibling
transcript. A conversation message *claiming* it ran ("verify green") is not
proof; note the claim in your verdict and check whether repo edits happened
after it (the obligation re-ripens).

### 4e — compile enforcement proposals

    python3 SCRIPTS/compile.py --work WORK

This writes `WORK/enforcement/` — a PROPOSALS.md dossier per rule, a generic
guard script, its per-rule config (warn-mode by default; defiance-proven
rules start at block), and a settings snippet. **Never install any of it
yourself; never edit the user's `.claude/settings.json`.** Goodhart caution
(citation id `specbench`): a visible pattern-gate can be satisfied without
honoring the rule — where a rule has a real outcome (tests pass, build
green), prefer a gate that runs the outcome over one that greps a pattern. Tell the user
where the proposals live and that they are review-then-arm.

### 4f — gap analysis: what the sessions dictate that the file never says

    python3 SCRIPTS/mine.py --work WORK

Read `WORK/candidates.json` and compare the surviving groups against the
rulebook: a recurrent signal (correction cluster, failed→fixed command
pair, recurring user denial) that matches NO existing rule is a rule the
user keeps dictating by hand, session after session. Judge as in Mode B2
below — decline one-offs and `stale` groups (automode blocks are already
excluded by the miner). For each
accepted miss, add a diagnosis with state `undocumented` (severity `warn`,
evidence = 1–2 excerpts), and when there are enough to matter, write
`WORK/chart.json` with `"mode": "gap"` (schema at the top of `generate.py`)
and run `python3 SCRIPTS/generate.py --work WORK` to emit
`PROPOSED-ADDITIONS.md`. Mind the combined budget: proposed additions must
not push the surface past the size target this same exam just graded.

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
    {"ref": "the exact ref string from refcheck.json", "line": 46,
     "reason": "why it is a false positive (route not file, MIME type, described as deleted, …)"}
  ],
  "rule_verdicts": {
    "R1": {"verdict": "healthy|ignored|mixed|inert|unmeasured|abandoned|undocumented",
           "note": "one line of judgment; 'abandoned' = the repo's own history contradicts the rule (e.g. git shows the team doing the banned thing routinely) even if sessions were inert"}
  },
  "diagnoses": [
    {"state": "dead-ref|stale|vague|ignored|inert|redundant|contradictory|oversized|accretion|generated-unpruned|undocumented",
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
  "followup": ["re-run cadence; transcript-retention advice; what to fix first"],
  "share_note": "one quotable line for the public share card — dry doctor's wit backed by the findings. STRICT safety: no file paths, no rule text, no quotes from the repo, no session ids, nothing repo-identifying; aggregate truths only (e.g. 'The loudest rule was the broken one.'). Omit the field to use a deterministic fallback."
}
```

Rules for this stage:
- **Every diagnosis needs evidence** (a quoted line, a metric, a failed check)
  and, where one exists, a citation id. List the valid ids and what each
  source claims with `python3 SCRIPTS/report.py --list-citations` — use only
  those ids, and only where the source actually supports the point. A check with no official or research
  backing is stated as a heuristic in its `detail`.
- **Severity honestly**: `critical` = the file lies to the agent (dead refs,
  drifted claims, contradictions) or content is being skipped (4 MiB);
  `warn` = costs context or reduces adherence (oversized, emphasis
  saturation, accretion); `info` = worth knowing.
- **Structure-only findings carry a caution**: the one factorial study found
  no structural effect in its tested range (citation id `mcmillan`) — do not
  present size/position folklore as causal fact. Content findings (dead refs,
  drift) need no such hedge.
- **Grade rubric**: A = no criticals and at most 2 warns; B = no criticals
  and 3 or more warns; C = 1–2 criticals; D = 3+ criticals; F = the file is
  actively misleading (mostly dead/drifted) or unloadable. A pointer-style
  CLAUDE.md with a healthy target grades on the target.
- Cannot-fix scopes (ancestor/user/managed files) may generate `info`
  diagnoses only.
- **Never mention this tool's version numbers in report content** (diagnoses,
  notes, follow-ups, chief complaint). The renderer stamps the version in the
  report footer; content reads timelessly — a reader doesn't know or care
  what "v0.2" means.
- **Pointer repos are usually cross-agent repos.** When the patient is an
  AGENTS.md reached via a pointer, it likely serves Cursor/Codex/Copilot too —
  prescriptions that relocate content into Claude-only surfaces
  (`.claude/rules/`, skills, hooks) hide it from those agents. Still prescribe
  them when right, but state the trade-off in the prescription ("Claude-only;
  other agents reading AGENTS.md will lose this") and prefer in-file fixes for
  content every agent needs.

## Stage 6 — report

    python3 SCRIPTS/report.py --work WORK

Then generate the share-safe card and badge:

    python3 SCRIPTS/card.py --work WORK

`card.svg` (postable checkup card) and `claude-md-health.svg` (README badge)
land next to report.html. Both are aggregate-only by construction — but eye
the card once anyway before telling the user it is safe to post. Offer the
badge snippet the script prints for their README.

Open or send the resulting `report.html` to the user, and summarize in chat:
grade, chief complaint, the top 3 findings, and the single highest-value
prescription. Tell the user where the report lives. If report.py printed an
INCOMPLETE warning, say which stage was missing and why.

## Mode B — the chart-less patient (no memory file? mine one)

Route here when intake found NO memory files at all, or when the user asked
to *generate* a CLAUDE.md / hooks / lint suggestions from their history —
but if the repo already HAS a memory file, never run Mode B: run the normal
exam and satisfy the generate request through Stage 4f (gap analysis,
`"mode": "gap"` → PROPOSED-ADDITIONS.md), so the existing file stays the
patient and the intake framing ("no memory file exists") stays true.
The transcripts already contain the unwritten rulebook: corrections the
user keeps typing, commands that fail until the right one runs, facts
re-derived at every session start, tool calls the user rejects. Mode B
takes a history and writes the initial chart.

Run Stages 2 and 3 first anyway — on an empty surface they finish instantly,
keep the manifest honest, and "0 tokens loaded every session" is the
patient's baseline vital.

### B1 — condense and mine

    python3 SCRIPTS/sessions.py --work WORK
    python3 SCRIPTS/mine.py --work WORK

`candidates.json` holds mechanically pre-filtered signals in five families
(corrections, failure_recovery, rediscovery, denials, preambles) plus a
startup-tax estimate. The lexical markers are calibrated to ~65–75%
precision — YOU are the judge pass; nothing in this file is a rule yet.

### B2 — judge the candidates (your judgment)

Triage every entry:
- **A rule** states something durable the user would still endorse: repeated
  corrections that converge ("use pnpm", "never push directly"),
  failed→fixed pairs whose fix is systematic (wrong runner, wrong dir,
  missing env var), recurring `user-rejected`/`permission-rule` denials.
  Write it as one imperative line.
- **A fact** is repo knowledge the agent keeps re-deriving: build/test
  commands from rediscovery groups, layout/context from preamble clusters.
- **Decline** one-off taste, task-specific instructions, anything flagged
  `stale` (the repo may have moved past it), and excerpts you cannot
  confidently generalize. (Auto-mode classifier blocks are already excluded
  by the miner — they appear only as `meta.automode_blocked`; do not
  resurrect them.) Record notable declines with reasons — the report
  discloses them.
- The recurrence gates already ran for the GROUPED families
  (failure_recovery, rediscovery, denials, preambles). Corrections are
  ungated — any single flagged message reaches you — so judge them hardest;
  a one-off correction is only a rule if its content is plainly durable.
  Then apply the meaning test to everything: *would the user bet on this
  line?* When unsure, decline — a mined draft earns trust by being small.
  And spot-check recall: the pre-filter misses bare factual corrections
  without marker words (`meta.known_gaps`); skim one or two condensed
  sessions' user texts if the yield looks thin.

### B3 — validate mined rules through the backtest (receipts)

For each accepted rule that is mechanically checkable, write a standard
`WORK/rulebook.json` entry (schema at the top of `backtest.py`; set
`"source": {"file": "mined-from-history", "line": 0}`, classify its
enforcement, give it an `echo_regex`), then:

    python3 SCRIPTS/backtest.py --work WORK
    python3 SCRIPTS/compile.py --work WORK

The backtest counts are the rule's receipts — a mined rule whose matcher
finds nothing in the very history that suggested it is a mining false
positive: drop it. Sample-verify fires exactly as in Stage 4d. compile
writes review-then-arm hook proposals for hook-class mined rules — born
mechanized: the best CLAUDE.md line is the one a guard enforces.

### B4 — write the chart and generate the draft

Write `WORK/chart.json` (schema at the top of `generate.py`): accepted facts
and rules with `occurrences`/`sessions` from mining or backtest, per-item
`evidence` excerpts, `startup_tax` (copy `est_tokens`/`sessions` from
candidates.json — the estimate is attributed to the recurring discovery
commands' own records and results, so quote it as exactly that, an
estimate), and your `declined` list. Then:

    python3 SCRIPTS/generate.py --work WORK

This assembles `PROPOSED-CLAUDE.md` next to the report — receipts ride in
HTML comments, which Claude Code strips at load, so they cost the adopter
nothing. It exits nonzero if the draft breaks the official 200-line target:
the doctor does not prescribe the disease it diagnoses. **Never copy the
draft into the repo yourself** — adoption is the user's move.

### B5 — diagnosis, report, card

Proceed to Stages 5 and 6 as usual. Mode B specifics:
- `chief_complaint`: the absence plus its cost, with evidence ("No memory
  file exists; N sessions show M recurring rules dictated by hand").
- **Grade the gap, not the void**: D when the history shows recurring
  unwritten rules being re-dictated or violated; C when the mined chart is
  thin. F stays reserved for actively misleading files — absence is not
  deception.
- `rule_verdicts` for backtested mined rules use verdict `undocumented`
  (they cannot be "ignored" — there was no file to ignore).
- The report renders the Initial chart section from `chart.json` and the
  card switches to intake stats automatically. Tell the user where
  `PROPOSED-CLAUDE.md` lives, that every line carries its receipt, and that
  hook proposals (if any) are review-then-arm.

## Conduct

- Everything runs locally; never send file contents anywhere.
- Quote at most ~2 lines from any file in evidence.
- In a headless or background run, do not try to "open" the report — state
  its path (report.html lands in the work directory's PARENT, next to
  report.json) and summarize it.

<p align="center">
  <img src="assets/doctor.svg" width="112" alt="pixel robot doctor">
</p>

# claude-md-doctor

**Give your CLAUDE.md a checkup.** A Claude Code skill that examines your repo's
agent-instruction files the way a physician examines a patient — vitals, lab work,
diagnoses, prescriptions — and hands you a report that cites its evidence.

> Everyone else lints the file or grades the sessions. claude-md-doctor
> cross-examines the file against reality — and cites receipts.

## What the exam covers (v0.1)

- **Vitals** — effective size vs the official guidance (*"target under 200 lines
  per CLAUDE.md file"* — [Claude Code memory docs](https://code.claude.com/docs/en/memory)),
  estimated token cost per session, structure, and pathology markers: stock `/init`
  boilerplate never pruned, emphasis saturation, changelog accretion.
- **Records check** — does everything the file points at exist? Dead file paths,
  paths from a teammate's machine, `@imports` that don't resolve, `pnpm`/`make`
  commands with no matching script, `.claude/rules/` scopes that match zero files.
- **Checkable claims** — countable assertions ("3,540 tests across 374 files",
  "12 UI components; no dialog") verified against the repo. Inlined numbers rot;
  the doctor catches them.
- **The report** — a single self-contained HTML page: chart grade, chief
  complaint, per-finding evidence, and concrete prescriptions, each footnoted
  with the official doc or study behind it (the evidence base lives in
  [docs/RESEARCH.md](docs/RESEARCH.md)).

It understands the real memory surface: `CLAUDE.md`, `.claude/CLAUDE.md`,
`CLAUDE.local.md`, nested files, `.claude/rules/*.md` (with `paths:` scopes),
`@imports` (depth 4, backtick-aware), `claudeMdExcludes`, ancestor directories —
and it treats the pointer-to-`AGENTS.md` pattern as healthy, examining the target.

## Coming in v0.2 — the part nobody else does

**The backtest.** Your own Claude Code session transcripts
(`~/.claude/projects/…`) already record whether past sessions actually followed
each rule in your CLAUDE.md. v0.2 decomposes the file into rules and replays
them against that history: which rules are followed, which get ignored, which
never come up at all — with receipts. Research shows agents silently skip
mandated steps while outputs still look fine; only behavioral evidence catches
that.

## Install

As a plugin (recommended):

```
/plugin marketplace add tx871217/claude-md-doctor
```

Or bare: copy `skills/claude-md-doctor/` into `~/.claude/skills/`.

Requires Python 3.9+ (standard library only — nothing to install).

## Use

In any repo, in a Claude Code session:

```
/claude-md-doctor
```

The report lands in `.claude-md-doctor/report.html` (plus machine-readable
`report.json`). Everything runs locally; nothing leaves your machine.

## Honesty policy

Every prescription carries an evidence tier — official doc, controlled study,
corpus study, or plainly-labeled heuristic — and the report states the tensions
in the research instead of hiding them (e.g., the one factorial study found no
structural effect of file size in its tested range, while content pruning has
strong causal backing). See [docs/RESEARCH.md](docs/RESEARCH.md) for the full
evidence base, ~30 primary-verified sources.

## Status

v0.1 (static exam) — working; first reports generated. v0.2 (session backtest)
is the headline release and under active development. Issues and PRs welcome.

## License

MIT. claude-md-doctor is an independent open-source project, not affiliated
with Anthropic. CLAUDE.md and Claude Code are products of Anthropic, PBC.

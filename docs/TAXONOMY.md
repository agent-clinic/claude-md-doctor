# The taxonomy: three enforcement classes, four failure causes

The doctor's two core ideas, in full. Evidence for every claim:
[RESEARCH.md](RESEARCH.md).

## Part 1 — Enforcement classes: what's the cheapest reliable detector?

Every *directive* in a CLAUDE.md/AGENTS.md (not informational content — facts
and API knowledge are never forced into rule classes) gets exactly one class:

| Class | Detector | Binds | Timing |
|---|---|---|---|
| **`hook`** | deterministic gate over the *event stream* (tool calls) | the agent | prevents — fires before damage |
| **`linter`/`test`** | static analysis over *artifacts* (code, configs, commit messages) | every agent **and every human** | edit-time / CI |
| **`judge`** | an LLM audits the artifact or transcript window | audit only | post-hoc, costs tokens per check |

- **Hook subtypes**: bash-gates (command regex), edit-gates (path/content
  regex), stop-gates (finish-ordering: "run X after the last edit"),
  tool-input gates (regex over any tool parameter), output gates (scan the
  final message — e.g. reply-language), and windowed/statistical detectors
  (session-shape rules: edit-streaks without verification, cadences via
  event timestamps).
- **Linter scope**: `file` rules are near-free per edit; `project` rules
  (import-graph boundaries, unused exports, public-API baselines) rebuild a
  graph — still batch and serverless. LSP is only the *human's* live delivery
  channel for this class; the agent's equivalent is a PostToolUse hook
  running the linter on the just-edited file.
- **Judge reliability has a ceiling** worth stating: prose procedures are
  followed at ~56–68% step-adherence (SIGIL), and the best models satisfy
  all constraints of a complex instruction only ~27% of the time (AGENTIF).
- **Not a fourth class**: a rule even a judge couldn't score is not a rule —
  it's the `vague` diagnosis. Rewrite it into something checkable, or delete
  it.

**Two reframes before surrendering a rule to `judge`:**

1. *Event-ordering*: semantic-feeling rules are often mechanical in the
   transcript — "read the design before coding" is just a Read-event
   preceding an Edit-event.
2. *Standing-invariant*: procedure-feeling rules are often graph invariants —
   "when creating a function in `func.tsx`, check it's only used by the
   frontend" becomes "`func.tsx` may only be imported from
   `src/frontend/**`", which a dependency-boundary linter enforces in batch.

**Fields that matter**: `against_prior` records whether the rule opposes what
a frontier model would do unprompted — models comply 3.6–7.4pp worse on
against-prior rules (Harness-IF), so high compliance on a *with-prior* rule
may be coincidence rather than obedience: a redundancy candidate, not a
success story. `current_layer` records enforcement that *already
exists* (a discipline test, a lint rule, a CI check — in mature repos this is
the most common finding: the prose is a healthy pointer to an existing law);
`adjudication: judge` marks soft rules ("unless requested", "where possible")
whose detector is mechanical but whose exceptions need judgment — armed as
warn-mode only.

Across ~135 directives classified from a dozen real-world files, the split is
roughly **hook 33% / linter 38% / judge 24% / vague 4%** — genre-dependent
(ops files skew hook, style guides skew linter, conduct rules skew judge) —
with one robust invariant: **the enforceable share (hook + linter) is
~70±5% in every slice.** Most of your rulebook could be laws instead of
requests.

## Part 2 — Failure causes: why did a rule get violated?

The backtest replays every rule against the repo's own session transcripts.
Each violation is triaged by context state — because the *cause* picks the
*medicine*:

| Cause | Signature | Medicine |
|---|---|---|
| **defiance-proven** | the agent *echoed the rule in its own words*, then violated it | **block-mode gate** — the reminder already happened and lost |
| **defiance** | violated in fresh context (early turn, low occupancy) | hard enforcement (warn-hook, then block); reminders can't fix it |
| **dilution** | violated late in a long, heavy session — in-window but drowned | soft first: slim the file, move the rule to point-of-use, PostToolUse nudge |
| **absence** | a *non-root* rule violated after a compaction boundary | re-injection (SessionStart/PreCompact hooks, path-scoped rules) — never blocking |

Proof strength descends in that order: echo-then-violate is evidence;
fresh-context is inference; the last two are context-state proxies (turn
depth, byte-offset occupancy, compaction markers in the transcript).

Why this matters: research shows rules fail *while demonstrably seen* — with
retrieval memory, 57.5% of applicable preference checks are still violated
(TRACE), and instruction-following decays within a session even when the
file loaded at the start (McMillan). So "add a reminder" is only the right
fix when the cause says the rule was drowned or dropped — and never when the
agent recited the rule and broke it anyway. The doctor's arming ladder
(**reminder → warn-hook → block-hook**) places each rule using its own
violation forensics instead of its author's temperament.

Compiled enforcement is what actually moves behavior: converting rules into
runtime checks cuts violations from ~100% to 2–38% (TRACE), and moving a
procedure from prose into scripts lifts step-adherence from 56% to 86%
(SIGIL). Prose is a request. The taxonomy tells you which of your requests
could be laws — and the triage tells you how strongly to pass each one.

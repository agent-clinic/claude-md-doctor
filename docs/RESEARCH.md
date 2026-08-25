# The evidence base

claude-md-doctor's report cites evidence the way a doctor cites studies. This file is the
curated map: **finding → the doctor check it informs → citation**. Every prescription in
the report footnotes an entry here, labeled with its evidence tier.

**Evidence tiers**: `official` (Anthropic docs/engineering) · `causal` (controlled study)
· `corpus` (empirical study of real files) · `mechanism` (research on the underlying
capability) · `consensus` (practitioner writing, no controlled test) · `heuristic`
(ours; no external backing — labeled as such in the report).

Verification status: every entry below was primary-source-verified (URL fetched directly)
on 2026-08-24 unless marked otherwise.

---

## 1. Does the file even help? (causal evidence)

**Gloaguen, Mündler, Müller, Raychev, Vechev (ETH Zurich SRI) — "Evaluating AGENTS.md:
Are Repository-Level Context Files Helpful for Coding Agents?"** arXiv:2602.11988
(v1 Feb 2026, v2 Jun 2026). Agents: Claude Code, Codex, Qwen Code; models incl.
Sonnet-4.5, GPT-5.2; SWE-bench Lite (LLM-generated files) + CTXbench (138 instances,
developer-committed files).
- Verified v2 numbers: LLM-generated files change resolve rate **−0.5%** (SWE-bench,
  p=0.87) and **−2%** (CTXbench, p=0.37); developer-written **+2.4%** (p=0.21, not
  significant) but **significantly better than LLM-generated (p=0.038)**; cost
  **+20%/+23%**, +2.5–3.9 extra steps.
- ⚠️ **Citation hygiene**: the widely-circulated "human +4% / LLM −3%" figures match
  neither paper version — secondary-reporting drift. Cite v2's numbers above.
- **Agents DO comply with what's written**: `uv` used 1.6×/instance when the file
  mentions it vs <0.01× when not; repo-specific tools 2.5× vs <0.05×. Repo overviews
  don't even reduce steps-to-first-file-interaction. v1 verbatim: "human-written context
  files should describe only minimal requirements."
- → Informs: the doctor's core stance. Keep concrete deviant directives (measurably
  followed), delete narrative/derivable overviews (cost without benefit), treat every
  line as a cost until proven otherwise. Severity boost for the `/init`-boilerplate
  detector.

**The neighborhood** (via the citation graph):
- **Khatri**, arXiv:2607.27250 — two-agent ablation, 288 runs: context strategy gave no
  correctness improvement (effects bounded ≤10–15pp); failures traced to implementation
  skill, not missing repo knowledge. → corroborates derivable-content pruning.
- **Shepard & Albrecht — "Probe-and-Refine"**, arXiv:2606.20512 — the counterpoint:
  *iteratively refined* guidance 33.0% vs static 28.3% vs unguided 25.5% (p<0.001) on
  SWE-bench Verified. → files are improvable, not just deletable — the doctor's
  prescriptions framing has causal backing.
- **ZORO**, arXiv:2604.15625 — rules files "remain passive: it is not immediately
  apparent when rules are being used or followed, or how to improve them." → the
  doctor's raison d'être in one sentence.
- **RepoComplianceBench**, arXiv:2607.26819 — agents "almost never proactively retrieve
  the contribution rules" and never refuse in AI-banned repos. → trajectory-judged
  compliance methodology precedent.
- **OctoBench**, arXiv:2601.10343 — 7,098 checklist items: "a systematic gap between
  task-solving and scaffold-aware compliance" — models solve the task while violating
  standing constraints. → task success and rule adherence must be scored separately,
  which is exactly the backtest's split.

**McMillan — "Instruction Adherence in Coding Agent Configuration Files: A Factorial
Study of Four File-Structure Variables."** arXiv:2605.10039 (2026). 1,650 Claude Code
CLI sessions manipulating file size, instruction position, file architecture, and
cross-file contradictions.
- **No detectable structural effect** after multiple-testing correction, in the tested
  range. Structure lint (position, splitting) has weaker causal evidence than folklore
  claims.
- Compliance **decays within-session**: ~5.6% lower odds of adherence per additional
  generated function (non-monotonic), and varies by task type.
- → Informs: (a) honesty labels — structure-based diagnoses cite this as a caution and
  carry `consensus`-tier severity, not `causal`; (b) the depth-indexed adherence metric
  gets a real coefficient; (c) the strongest justification for the backtest itself:
  behavioral evidence outranks structural lint.

**The tension, encoded**: Anthropic's guidance says bloat causes instruction loss
(`official`); the one factorial test found no structural effect in its tested range
(`causal`, narrow); ETH found files cost tokens without lifting success but directives
are followed (`causal`). Net evidence-based prescription: prune derivable/narrative
content aggressively, keep concrete directives, move episodic workflows to on-demand
skills, and route must-happen rules to hooks. The doctor's report states this tension
rather than hiding it.

## 2. What's actually in real files (corpus baselines)

**Chatlatanagulchai, Li, Kashiwa, Reid, et al. — "Agent READMEs: An Empirical Study of
Context Files for Agentic Coding."** arXiv:2511.12884 (2025, rev. 2026). 2,303 context
files (AGENTS.md/CLAUDE.md etc.) from 1,925 repos.
- Content dominated by test procedures (75.9%), implementation details (70.8%),
  architecture (68.1%); **security (14.8%) and performance (14.5%) nearly absent**.
- Files "evolve like configuration code through frequent, small additions" and become
  hard to read — churn-without-pruning is the natural failure mode.
- → Informs: the population baseline the report diffs against ("your file vs the wild"),
  a "missing non-functional guidance" check, and the freshness/accretion diagnosis.

**Chatlatanagulchai, Thonglek, Reid, Kashiwa, et al. — "On the Use of Agentic Coding
Manifests: An Empirical Study of Claude Code."** PROFES 2025, arXiv:2509.14744.
253 CLAUDE.md files from 242 repos.
- Shallow hierarchies (one main heading + subsections), dominated by operational
  commands, implementation notes, high-level architecture; authoring guidance is a
  documented developer pain.
- → Informs: CLAUDE.md-specific structure norms, and the market gap this tool fills.

**Jiang & Nam — "Beyond the Prompt: An Empirical Study of Cursor Rules."** MSR 2026,
arXiv:2512.18925. 401 OSS repos with cursor rules.
- Five-theme content taxonomy: Conventions, Guidelines, Project Information, LLM
  Directives, Examples. Heavy duplication: **~28.7% duplicated lines** across a repo's
  rules files.
- → Informs: the §5 rule-taxonomy classifier gets a validated ancestor, and the
  cross-file duplication check gets a corpus prevalence number.

## 3. Anthropic's own engineering canon (`official`)

**"Effective context engineering for AI agents"** (Sep 2025,
anthropic.com/engineering/effective-context-engineering-for-ai-agents).
- Context is "a finite resource with diminishing marginal returns" — an "attention
  budget"; aim for "the smallest possible set of high-signal tokens."
- The "right altitude": instructions "specific enough to guide behavior effectively, yet
  flexible enough to provide strong heuristics" — the theoretical basis for the
  `vague` diagnosis at one end and over-specification at the other.
- Prefer just-in-time retrieval via lightweight identifiers over pre-loading — backs the
  pointer/progressive-disclosure pattern the gold-standard corpus shows.

**"Claude Code best practices"** (code.claude.com/docs/en/best-practices).
- The deletion test: "Would removing this cause Claude to make mistakes? If not, cut it.
  Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"
- Include/exclude table (exclude anything derivable from code); sparse emphasis ("if you
  emphasize many lines, none of them stands out") — the emphasis-density check's
  official basis; "anything that must always happen belongs in a hook."
- Domain workflows "only relevant sometimes" belong in skills — the `move-to-skill`
  prescription verbatim.

**Memory doc** (code.claude.com/docs/en/memory): "Size: target under 200 lines per
CLAUDE.md file. Longer files consume more context and reduce adherence." (The number is
on this page — NOT on best-practices; cite precisely.) Plus: 4 MiB hard skip, HTML
comments stripped, import depth 4, MEMORY.md loads first 200 lines / 25KB.

**"Equipping agents for the real world with Agent Skills"** (Oct 2025).
- Progressive disclosure in three levels (metadata → SKILL.md → bundled files); split
  when "unwieldy"; name/description are the trigger — the future SKILL.md doctor's spec.

**"Managing context on the Claude Developer Platform"** (Sep 2025,
claude.com/blog/context-management).
- Memory tool + context editing = **+39%** over baseline on internal agentic eval;
  **84% token reduction** on a 100-turn eval. Store "debugging insights and architectural
  decisions" — hard-won, non-rederivable state. → MEMORY.md content rubric.

**"Writing effective tools for AI agents"** (Sep 2025) + **"How we built our multi-agent
research system"** (Jun 2025).
- Description wording alone moved SWE-bench SOTA; an agent that rewrites flawed tool
  descriptions produced a **40% decrease in task completion time**. → A skill/tool
  description is load-bearing infrastructure; quality is measurable, not cosmetic.

## 4. Why "move it to a skill" works (`causal`/`mechanism`)

**Wang, Mao, Fried, Neubig — "Agent Workflow Memory."** arXiv:2409.07429 (2024).
- Inducing reusable workflows from past trajectories and **selectively** injecting them:
  +24.6% relative (Mind2Web), **+51.1% relative (WebArena)**, with fewer steps.
- → The causal warrant for the `move-to-skill` prescription: recurring workflows belong
  in on-demand memory, not the always-loaded file.

**Wang, Gandhi, Neubig, Fried — "Inducing Programmatic Skills for Agentic Tasks (ASI)."**
arXiv:2504.06821 (2025).
- Skills as executable, verified programs beat text-based skills: +23.5% over baseline,
  +11.3% over text-skill variants, 10.7–15.3% fewer steps.
- → Prefer skills that bundle runnable scripts; flag prose-only skills with no
  verification path.

**Huang et al. — "From Raw Experience to Skill Consumption."** arXiv:2605.23899 (2026).
- Model-generated skills help on average but show **non-trivial negative transfer** — a
  bad skill actively hurts; extraction quality is decoupled from model scale.
- → Skills are not free wins: the future SKILL.md doctor tests trigger precision, not
  presence.

**Dantanarayana, Kashmira, Tang, Mars — "SIGIL: Compiling Agent Skills into Typed
Harnesses."** arXiv:2607.27309 (Jul 2026). (Abstract-level verification; skills/models
not named in the abstract.)
- Across 30 skills and two model generations, **a prose agent performs only 56% of the
  steps its own skill mandates — while producing artifacts that pass output checks**;
  prose adherence swings 56%→68% across model generations.
- Compiling the skill into a typed harness (AG-IR: model-owned cognition separated from
  code-owned mechanism): **86% step adherence, model-independent, 2.3× completion,
  0.58× tokens** — a mandated step executes "because it is represented in the program
  structure rather than because the model correctly interprets a prose instruction."
- → Three uses: (1) **backtest methodology** — output checks miss silent procedure
  violations, so adherence must be judged on the behavior stream, which is exactly the
  matcher-over-tool-calls design; (2) **the procedure ladder** — prose-in-CLAUDE.md <
  prose skill (~56–68% followed) < script-carrying skill (ASI +11.3%; SIGIL 86% at
  0.58× tokens) < hook (deterministic) — the future SKILL.md doctor checks what fraction
  of a skill's mandated steps live in scripts vs prose; (3) **reflexively** — this
  project's own SKILL.md keeps control flow in scripts and emits a work-state manifest
  so the report can self-verify every exam stage ran.
- Neighborhood: **SkillSmith** (arXiv:2605.15215) — same skill-compilation direction,
  boundary-guided runtime interfaces.

**Kevin, Raghavan, Puget, et al. (NVIDIA) — "Evaluating Skills, Not Just Agents:
Agentic Continuous Evaluation of Skills (ACES)."** arXiv:2608.20614 (Aug 2026).
Paired with/without-skill trials; 145 real skills, 947 scored cases; open-source
(NVIDIA SkillEvaluator). (Abstract-level verification.)
- Mean composite "Skill Lift" 0.2134 — but **positive lift in only 72.8% of paired
  cases**: ~27% of production skills add zero or negative value. Enterprise-scale
  corroboration of the negative-transfer finding.
- **Structural scans correlate at Spearman ρ = 0.14 with judged skill value** — the
  sharpest number yet for "static linting barely predicts whether an instruction
  artifact helps."
- → Three uses: (1) positioning — the third leg of the static-is-weak-evidence stool
  (McMillan: no structural effect; ETH: overviews don't help; ACES: ρ=0.14) — the
  doctor's static stage stays an opening act, behavioral evidence is the product;
  (2) the future SKILL.md doctor measures *lift*, not presence; (3) methodological
  complement to the v0.2 backtest — ACES is the prospective paired trial (costs
  inference per eval), the backtest is the retrospective chart review (free
  history); triage retrospectively, confirm expensive cases prospectively.

**Hsieh et al. — "Tool Documentation Enables Zero-Shot Tool-Usage."** arXiv:2308.00675
(2023). Docs alone match few-shot demos; at scale, docs beat demos. → Invest in the
description before examples.

**Wang et al. — "Voyager."** arXiv:2305.16291 (2023). The original skill library:
curated, verified, description-indexed procedures compound ability (3.3× items, 15.3×
faster milestones) and transfer. → The lineage of the whole skills mechanism.

## 5. What memory research says (for the MEMORY.md doctor)

- **MemGPT** (arXiv:2310.08560): small always-loaded core + paged archival storage,
  self-edited — the architectural precedent for MEMORY.md's index + topic files and for
  capping the always-loaded tier.
- **Reflexion** (NeurIPS 2023, arXiv:2303.11366): lessons-from-failure stored verbally
  improve later trials (91% pass@1 HumanEval vs GPT-4's 80%) — reward memory entries
  carrying causal failure context ("avoid X, it caused Y") over bare facts.
- **Generative Agents** (UIST 2023, arXiv:2304.03442): recency/importance/relevance
  retrieval + periodic **reflection/consolidation**; append-only logs are not enough.
- **Memp** (arXiv:2508.06433): procedural memory must be "continuously updated,
  corrected, and deprecated" — flag never-revised, never-pruned memories.
- **A-MEM** (NeurIPS 2025, arXiv:2502.12110): linked Zettelkasten notes where new
  memories trigger updates of old ones — supports link-density and
  contradiction-accretion checks.
- **Episodic-memory position paper** (arXiv:2502.06975): persist instance-specific
  episodes with context, not only distilled generalities.
- **Surveys**: "Rethinking Memory in LLM-based Agents" (arXiv:2505.00675) — six atomic
  operations: consolidation, updating, indexing, forgetting, retrieval, condensation.
  A healthy memory surface evidences all six; **most real MEMORY.md files only ever do
  "add."** "Memory in the Age of AI Agents" (arXiv:2512.13564) — classify entries as
  factual / experiential / working; curation dynamics, not storage, are what fail.

## 6. Calibration numbers extracted

| Constant | Value | Source |
|---|---|---|
| Size target (per file) | 200 lines | official (memory doc) |
| Hard skip | 4 MiB | official (memory doc) |
| Startup warning | 40,000 chars | official (troubleshooting) |
| Healthy band observed in gold corpus | 40–180 lines | our §13 corpus |
| Context-file cost, no significant success lift | +20–23% tokens | ETH 2602.11988 (v2) |
| LLM-generated file effect | −0.5% to −2% (ns) | ETH 2602.11988 (v2) |
| Developer-written file effect | +2.4% (ns; > LLM-gen, p=0.038) | ETH 2602.11988 (v2) |
| Rule-count dose-response (best model) | 98.4% @100 → 84.8% @250 → 68.9% @500 | IFScale 2507.11538 |
| All-constraints satisfaction ceiling (agentic) | 27.2% ISR | AGENTIF 2505.16944 |
| Instruction-length cliff | ISR ≈ 0 past 6,000 words | AGENTIF 2505.16944 |
| Per-turn decay (system-message constraints) | ≈ −12.8pp/turn (84.8→33.7 over 5) | SysBench 2408.10943 |
| Multi-turn vs single-turn drop | −39% avg | Laban 2505.06120 |
| Within-session adherence decay | ~5.6%/function (odds) | McMillan 2605.10039 |
| Padding cost | 0.92 → 0.68 acc at +3k tokens; starts ~500 | Levy 2402.14848 |
| Compression upside | +21.4% at ~4× compression | LongLLMLingua 2310.06839 |
| Uppercase effect | +1.85pp acc; ~0 on reasoning models | 2608.03711 |
| Refined-guidance upside | 33.0% vs 25.5% unguided | Probe-and-Refine 2606.20512 |
| Prose-skill step adherence | 56% (→68% newer gen); outputs still pass | SIGIL 2607.27309 |
| Structural scans vs judged skill value | Spearman ρ = 0.14 | ACES 2608.20614 |
| Skills with zero/negative lift | ~27% (72.8% positive) | ACES 2608.20614 |
| Script-compiled skill adherence | 86%, model-independent, 0.58× tokens | SIGIL 2607.27309 |
| Duplicated lines across rules files | ~28.7% | Jiang & Nam 2512.18925 |
| Workflow-extraction lift | +51.1% rel. (WebArena) | AWM 2409.07429 |
| Memory-tool lift / token cut | +39% / −84% | Anthropic context-management |
| Content baseline (tests/impl/arch) | 75.9 / 70.8 / 68.1% | Agent READMEs 2511.12884 |

## 7. How many rules can a model actually follow? (`causal`)

**Jaroslawicz et al. — "How Many Instructions Can LLMs Follow at Once?" (IFScale)**,
arXiv:2507.11538 (2025). 500 keyword-instructions, 20 models.
- The dose-response curve: best model **100% at 10 instructions → 98.4% at 100 →
  84.8% at 250 → 68.9% at 500**; top reasoning models hold "near-perfect through 150+."
- Errors shift overwhelmingly to **omission** (rules silently dropped) as density rises —
  violations are silent, which is why only a backtest can find them.
- **Provenance closed**: HumanLayer's "~150–200 instructions" is a practitioner gloss of
  this paper (their post links it); the number isn't in the paper itself.
- → Calibrates the rule-count vital: an inventory of N rules maps onto this curve.

**AGENTIF** (Qi et al., arXiv:2505.16944, NeurIPS 2025 D&B Spotlight). 707 instructions
from 50 real agentic applications, avg 11.9 constraints each.
- Best model satisfies ALL constraints of an instruction (ISR) only **27.2%** of the
  time; constraint-level (CSR) 59.8. **ISR ≈ 0 past 6,000 words** of instruction.
- → Sets the health-score ceiling honestly (perfect adherence is not on the table even
  for a perfect file) and adds a hard size cliff to vitals.

**IFEval** (Zhou et al., arXiv:2311.07911) — 25 *verifiable* instruction types; the
template for our mechanical-vs-semantic rule split. **IFEval++/reliable@k**
(arXiv:2512.14754) — near-ceiling accuracy hides up to **61.8% drops** under paraphrase;
a rule that only works under one phrasing isn't reliable → backs the `vague` diagnosis.

**SysBench** (Qin et al., arXiv:2408.10943) — system-message constraints over 5-turn
conversations: GPT-4o decays **84.8% → 33.7% (≈ −12.8pp/turn)** on turn-dependent
sessions. CLAUDE.md is system-prompt-like content; this is the cleanest per-turn decay
slope available (2024-era models — caveat in the report). Corroborated on modern models
by **Laban et al.** (arXiv:2505.06120): **39% average multi-turn drop** across 200k+
simulated conversations. → Calibrates depth-indexed adherence bucketing.

## 8. Position and length effects (`causal`/`mechanism`)

- **Lost in the Middle** (Liu et al., TACL 2024, arXiv:2307.03172) — U-shaped position
  curve: content at the beginning or end outperforms mid-context. → rule-placement
  advice (critical rules first/last, never buried), consensus-tier until tested on
  instruction files specifically.
- **Chroma "Context Rot"** (Hong, Troynikov, Huber, 2025 technical report) — 18 models
  degrade with input length even on trivial tasks; a focused ~300-token prompt beats the
  same question in ~113k tokens of context; distractors compound. → every irrelevant
  CLAUDE.md line is haystack.
- **Levy, Jacoby, Goldberg** (ACL 2024, arXiv:2402.14848) — same task padded to 3,000
  tokens: accuracy **0.92 → 0.68**; degradation starts **beyond ~500 tokens** of
  padding. → the sharpest peer-reviewed "bloat is not free" number.

## 9. Compression (`causal`)

**LLMLingua** (EMNLP 2023) / **LongLLMLingua** (ACL 2024, arXiv:2310.06839) — up to 20×
compression at ~1.5-point cost; LongLLMLingua **+21.4% on NaturalQuestions at ~4×
compression** — removing filler doesn't just save tokens, it can *raise* performance.
→ the cut-decoration prescription's causal backing.

## 10. Does emphasis actually work? (`mechanism`, honest gaps marked)

- **"Attention is Case-Sensitive"** (Dillitzer et al., arXiv:2608.03711) — uppercasing
  target spans shifts **+2.06pp attention mass, +1.85pp accuracy** across 13 models;
  **near-zero effect on reasoning models**; alternating case hurts (−2.88pp). → caps do
  something, the effect is small, spent when saturated, and gone on reasoning models —
  the emphasis-density check cites this and the official "if you emphasize many lines,
  none stands out."
- **Formatting sensitivity**: Sclar et al. (ICLR 2024, arXiv:2310.11324) —
  meaning-preserving format changes swing accuracy up to **76 points** on smaller
  models; He et al. (arXiv:2411.10541) — template choice swings GPT-3.5 up to 40%,
  GPT-4 far more robust. → formatting is behaviorally load-bearing; auditing it is
  defensible.
- **Honest gap**: no rigorous study tests "IMPORTANT"/bold markers on *compliance in
  agentic settings*. The report marks bold/"IMPORTANT" claims as extrapolation from the
  casing study + official guidance.

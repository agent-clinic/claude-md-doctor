# The evidence base

claude-md-doctor's report cites evidence the way a doctor cites studies. This file is the
curated map: **finding → the doctor check it informs → citation**. Every prescription in
the report footnotes an entry here, labeled with its evidence tier.

**Evidence tiers**: `official` (Anthropic docs/engineering) · `causal` (controlled study)
· `corpus` (empirical study of real files) · `mechanism` (research on the underlying
capability) · `consensus` (practitioner writing, no controlled test) · `heuristic`
(ours; no external backing — labeled as such in the report).

Verification status: every entry below was primary-source-verified (URL fetched directly)
on 2026-08-24/25 unless marked otherwise.

## The index — every source in one line

| Source | What it says | How the doctor uses it |
|---|---|---|
| [Claude Code memory doc](https://code.claude.com/docs/en/memory) | "Target under 200 lines per CLAUDE.md file"; 4 MiB hard skip; comments stripped; root file re-injected post-compact | Size vitals thresholds; intake loader semantics; absence-cause scoping |
| [Claude Code best practices](https://code.claude.com/docs/en/best-practices) | Deletion test; "bloated files cause Claude to ignore your instructions"; sparse emphasis; hooks for must-happen rules | Prescriptions, emphasis-density check, move-to-hook advice |
| [Claude Code troubleshooting](https://code.claude.com/docs/en/troubleshooting) | Startup warning at 40,000 chars of memory | Combined-surface vital |
| [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Attention budget; "right altitude" of instructions; just-in-time retrieval over pre-loading | Theoretical frame for bloat/vague diagnoses; pointer-pattern endorsement |
| [Agent Skills post](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | Progressive disclosure; name/description are the trigger | Future SKILL.md checks; move-to-skill prescription |
| [Context management post](https://claude.com/blog/context-management) | Memory tool +39% success, −84% tokens; store non-rederivable state | MEMORY.md content rubric |
| [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) | Description wording alone moved SWE-bench SOTA | Skill/tool description quality checks |
| [Multi-agent system post](https://www.anthropic.com/engineering/built-multi-agent-research-system) | Rewritten tool descriptions → 40% task-time decrease | Same — descriptions are load-bearing |
| [ETH "Evaluating AGENTS.md"](https://arxiv.org/abs/2602.11988) | Context files cost +20–23% with no significant success lift; explicit directives ARE followed | Core stance: keep directives, cut narrative; /init-boilerplate severity |
| [McMillan factorial](https://arxiv.org/abs/2605.10039) | 1,650 sessions: no structural effect of size/position; ~5.6%/function in-session decay | Structure-caution labels; depth-indexed cause triage |
| [Khatri ablation](https://arxiv.org/abs/2607.27250) | Context strategies gave no correctness improvement (≤10–15pp bound) | Corroborates derivable-content pruning |
| [Probe-and-Refine](https://arxiv.org/abs/2606.20512) | Iteratively refined guidance 33.0% vs 25.5% unguided | Files are improvable — the prescriptions half |
| [ZORO](https://arxiv.org/abs/2604.15625) | Rules files "remain passive: not apparent when rules are followed" | The product's raison d'être |
| [RepoComplianceBench](https://arxiv.org/abs/2607.26819) | Agents almost never retrieve contribution rules | Trajectory-judged compliance precedent |
| [OctoBench](https://arxiv.org/abs/2601.10343) | Systematic gap between task-solving and scaffold compliance | Backtest scores adherence separately from success |
| [Agent READMEs](https://arxiv.org/abs/2511.12884) | 2,303 files: tests 75.9%/impl 70.8%/arch 68.1%; churn without pruning | "Your file vs the wild" baseline; accretion diagnosis |
| [Claude Code manifests study](https://arxiv.org/abs/2509.14744) | 253 CLAUDE.mds: shallow hierarchies, command-dominated | CLAUDE.md structure norms |
| [Jiang & Nam cursor rules](https://arxiv.org/abs/2512.18925) | Five-theme taxonomy; ~28.7% duplicated lines across rules files | Rule-taxonomy ancestor; cross-file duplication check |
| [XTrace surface-bloat post](https://xtrace.ai/blog/too-many-claude-skill-files) | 60 files ≈ 64k standing tokens; consolidate → router → invariants | Combined-surface diagnosis + escalating ladder |
| [Unblocked 7-step audit](https://getunblocked.com/blog/audit-fix-bloated-claude-md/) | The manual audit process | What the skill automates |
| [IFScale](https://arxiv.org/abs/2507.11538) | 98.4% adherence @100 rules → 68.9% @500; errors become silent omissions | Rule-count vital; why only a backtest catches violations |
| [AGENTIF](https://arxiv.org/abs/2505.16944) | Best model satisfies all constraints 27.2%; ≈0 past 6,000 words | Honest score ceiling; size cliff |
| [IFEval](https://arxiv.org/abs/2311.07911) | 25 verifiable instruction types | Template for mechanical-vs-judge split |
| [IFEval++](https://arxiv.org/abs/2512.14754) | Up to 61.8% drops under paraphrase | `vague` diagnosis: one-phrasing rules aren't reliable |
| [SysBench](https://arxiv.org/abs/2408.10943) | System-message adherence −12.8pp/turn | Depth-indexed dilution triage |
| [Laban multi-turn](https://arxiv.org/abs/2505.06120) | 39% average multi-turn drop | Dilution corroboration on modern models |
| [Harness-IF](https://arxiv.org/abs/2608.11727) | Against-prior penalty 3.6–7.4pp; project files outrank skill/tool descriptions | `against_prior` field; move-to-skill precedence rider |
| [IHEval](https://arxiv.org/abs/2502.08745) | Conflicting instructions: best OSS model resolves at 48% | `contradictory` diagnosis evidence |
| [Instruction Hierarchy (OpenAI)](https://arxiv.org/abs/2404.13208) | Precedence is trained in | Against-prior mechanism; why some rules need hooks |
| [InFoBench](https://arxiv.org/abs/2401.03601) | DRFR: decompose into yes/no criteria, judge each | The backtest's unit of analysis; split-before-classify |
| [ComplexBench](https://arxiv.org/abs/2407.03978) | Constraint composition types | Compound-rule splitting |
| [CFBench](https://arxiv.org/abs/2408.01122) | Constraint taxonomy, requirement prioritization | Rule classification |
| [Multi-IF](https://arxiv.org/abs/2410.15553) | Per-turn decay 0.877→0.707 by turn 3 | Depth evidence |
| [CodeIF-Bench](https://arxiv.org/abs/2503.22688) | Repo context + interaction history degrade coding IF | Coding-specific dilution |
| [LIFBench](https://arxiv.org/abs/2411.07037) | Judge-free rubric scoring of IF stability in long contexts | Dilution measurement; judge-free verification |
| [Lost in the Middle](https://arxiv.org/abs/2307.03172) | U-shaped position curve | Rule-placement advice (consensus tier) |
| [Chroma Context Rot](https://www.trychroma.com/research/context-rot) | 18 models degrade with length; 300-token focus beats 113k context | Every irrelevant line is haystack |
| [Levy padding](https://arxiv.org/abs/2402.14848) | 0.92 → 0.68 accuracy at +3k tokens; starts ~500 | The sharpest "bloat is not free" number |
| [LongLLMLingua](https://arxiv.org/abs/2310.06839) | +21.4% at ~4× compression | Cut-decoration prescription |
| [Attention is Case-Sensitive](https://arxiv.org/abs/2608.03711) | Caps +1.85pp; ~zero on reasoning models | Emphasis-density check, honestly tiered |
| [Sclar formatting](https://arxiv.org/abs/2310.11324) | Format changes swing accuracy up to 76pts | Formatting is behaviorally load-bearing |
| [He formatting](https://arxiv.org/abs/2411.10541) | Template choice swings GPT-3.5 up to 40% | Same |
| [SIGIL](https://arxiv.org/abs/2607.27309) | Prose skills: 56% step adherence; compiled: 86% at 0.58× tokens | Behavior-not-outcomes backtest; scripts-carry-procedure; ladder |
| [SkillSmith](https://arxiv.org/abs/2605.15215) | Skill-compilation sibling | Neighborhood reference |
| [TRACE](https://arxiv.org/abs/2606.13174) | 57.5% violated with memory access; compiled checks → 2–38% | Compilation payoff; proven-defiance basis (rule echoed, then broken) |
| [Agent Workflow Memory](https://arxiv.org/abs/2409.07429) | Selectively-injected workflows +51.1% on WebArena | Move-procedures-to-skills prescription |
| [ASI](https://arxiv.org/abs/2504.06821) | Executable skills beat text skills +11.3% | Prefer script-carrying skills |
| [Voyager](https://arxiv.org/abs/2305.16291) | The original curated skill library | Skills-mechanism lineage |
| [Hsieh tool docs](https://arxiv.org/abs/2308.00675) | Docs alone match few-shot demos | Description before examples |
| [Model-generated skills](https://arxiv.org/abs/2605.23899) | Non-trivial negative transfer — bad skills hurt | Trigger-precision over presence |
| [ACES](https://arxiv.org/abs/2608.20614) | Structural scans ρ=0.14 vs judged value; ~27% skills zero/negative lift | Static-is-weak-evidence; measure lift, not presence |
| [MCP-smelly](https://arxiv.org/abs/2602.14878) | 97.1% of tool descriptions have smells; fixes +5.85pp but +67% steps | Closest analog; prescriptions-have-costs warning |
| [OpenSkillEval](https://arxiv.org/abs/2605.23657) | Many popular skills don't beat base agents | Redundancy/null-effect precedent |
| [ProcCtrlBench](https://arxiv.org/abs/2605.20251) | Trajectory normalization + 11-type defect ontology | Condense-then-backtest methodology sibling |
| [SpecBench](https://arxiv.org/abs/2605.21384) | Visible-check gaming: ~28pp holdout gap per 10× code size | Goodhart caution on hook compilation — prefer outcome-gates |
| [MemGPT](https://arxiv.org/abs/2310.08560) | Small core memory + paged archival storage | MEMORY.md index+topic-files architecture |
| [Reflexion](https://arxiv.org/abs/2303.11366) | Verbal failure-lessons improve later trials | Reward causal failure context in memories |
| [Generative Agents](https://arxiv.org/abs/2304.03442) | Reflection/consolidation beats append-only logs | Memory-consolidation precedent |
| [Memp](https://arxiv.org/abs/2508.06433) | Procedural memory must be updated, corrected, deprecated | Flag never-revised memories |
| [A-MEM](https://arxiv.org/abs/2502.12110) | Linked notes; new memories update old ones | Link-density / contradiction-accretion checks |
| [Episodic memory position](https://arxiv.org/abs/2502.06975) | Persist instance-specific episodes with context | Memory content rubric |
| [Memory survey (operations)](https://arxiv.org/abs/2505.00675) | Six atomic operations; most files only ever "add" | MEMORY.md health checklist |
| [Memory survey (functions)](https://arxiv.org/abs/2512.13564) | Classify factual/experiential/working; dynamics fail, not storage | Memory entry classification |

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

**"Too Many CLAUDE.md and Skill Files? 4 Fixes for Agent Memory Bloat"** — XTrace blog,
Jul/Aug 2026 (`consensus` tier — practitioner writing).
- Names the **aggregate-surface** failure mode a per-file view misses: 60 memory files
  averaging 800 words ≈ 64k tokens — a third of a 200k window spent before the first
  prompt; cites a real 187-file, four-folder setup with internal contradictions.
  Failure is silent degradation, not a loud error.
- Four escalating fixes that map onto the doctor's prescription ladder: consolidate
  duplicates ("30–50% reduction on the first pass" — pairs with the ~28.7% measured
  duplication below), a thin router/index over domain folders ("standing context cost
  becomes the size of the index rather than the corpus" — the pointer pattern the gold
  corpus shows), a one-screen always-on invariants file with procedures on demand, and
  retrieval as the architectural end-state.
- → Informs: a first-class **combined-surface diagnosis** (file count + total
  launch-loaded tokens + cross-file duplication/contradictions), not just per-file
  vitals; the mechanism it leans on (mid-context attention) is backed causally by
  Lost-in-the-Middle / Context Rot above.

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

**Zhou, Guo, Zhuang, et al. — "Getting Better at Working With You: Compiling User
Corrections into Runtime Enforcement for Coding Agents (TRACE)."** arXiv:2606.13174
(Jun 2026). (Abstract-level verification.)
- Names the core gap: **preference access ≠ preference compliance** — with Mem0
  memory, **57.5% of applicable preference checks are still violated**. Rules fail
  *while remembered*: direct causal support for the defiance failure-cause and for
  "prose/memory is a request."
- Pipeline = mine user corrections → rewrite as atomic rules → **compile into
  runtime checks that must pass before completion**. Compilation payoff:
  violations **100% → 2.0%** (OOD) / 37.6% (ID) on ClawArena coding tasks; honest
  limit: only → 60.5% on memory-intensive tasks — compilation is not universal.
- → Validates the v0.3 stack end-to-end (correction mining + decomposition +
  enforcement compilation) with measured deltas. Our differentiators remain:
  retrospective backtest before arming, native enforcement layers (hooks/linters
  binding humans too), cause-of-failure triage choosing arming strength. Their
  simulated user-in-the-loop benches (ClawArena/MemoryArena) are eval-design
  references.

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
| Preference violations despite memory (Mem0) | 57.5% | TRACE 2606.13174 |
| Against-prior compliance penalty | 3.6–7.4pp (mean 5.81) | Harness-IF 2608.11727 |
| Conflict-resolution accuracy (best OSS model) | 48% | IHEval 2502.08745 |
| Agent-instruction text with ≥1 quality smell | 97.1% | MCP-smelly 2602.14878 |
| Cost of "fixing" instruction text | +5.85pp success, +67% steps | MCP-smelly 2602.14878 |
| Visible-check vs holdout gaming gap | ~28pp per 10× code size | SpecBench 2605.21384 |
| Surface precedence | system ≈ project files ≈ user > tool/skill descriptions | Harness-IF 2608.11727 |
| Compiled-enforcement payoff | 100% → 2.0% (OOD) / 37.6% (ID) violations | TRACE 2606.13174 |
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

**Harness-IF** (Huang et al., arXiv:2608.11727, Aug 2026). 60 multi-turn coding
items from a 642-rule library, rules placed across the five surfaces a deployed
agent reads; 12 frontier models. (Abstract-level verification.)
- **Compliance vs coincidence**: "when a coding agent obeys a rule, it may simply
  have been going to do that anyway." Their Against-Prior Accuracy scores only
  rules opposing unprompted defaults (verified by re-running with the rule
  withheld): accuracy 72.1–85.9% but AP-Acc 66.1–78.6% — **every model worse on
  against-prior rules by 3.6–7.4 points (mean 5.81)**; aggregate scores overstate
  compliance by a model-specific margin.
- **Surface precedence does not follow prompt depth**: system prompts, project
  files, and user instructions rank **ahead of tool and skill descriptions**.
- → Two design consequences: (1) the backtest's `healthy` verdict splits —
  rules judged `against_prior: no` that show high compliance are
  **compliant-but-coincidental** → redundancy candidates (the deletion test
  applies), while against-prior compliance means the rule earns its cost; this
  turns the `redundant` diagnosis from vibes into method. (2) The move-to-skill
  prescription gets a rider: it is for *procedures* (load on invocation), never
  for *constraints* — a constraint demoted into a skill description measurably
  loses precedence. CLAUDE.md's high precedence as a "project file" is validated.

**The instruction-hierarchy pair** (via Harness-IF's citation graph; abstract-verified):
- **Wallace et al. (OpenAI), "The Instruction Hierarchy"** (arXiv:2404.13208) —
  models are *trained* to prioritize privileged instructions and ignore
  lower-ranked ones. This is the mechanism behind against-prior failures: a
  project-file rule fighting trained-in behavior starts at a disadvantage —
  the conceptual anchor for "this rule needs a hook because the prior will win."
- **IHEval** (NAACL 2025, arXiv:2502.08745) — 3,538 examples across
  system/user/history/tool priority levels: all models drop sharply when
  instructions **conflict** vs plain IF; the best open-source model resolves
  conflicts at only **48%**. → The evidence behind the `contradictory`
  diagnosis: conflicting rules aren't just untidy, they measurably degrade
  compliance — and which rule wins is not reliably the one you intended.
  (Harness-IF's complement: IHEval tests a *prescribed* hierarchy; Harness-IF
  measures precedence empirically.)

**InFoBench** (arXiv:2401.03601) — DRFR: decompose complex instructions into
simple yes/no criteria and score each (500 instructions → 2,250 criteria);
GPT-4 shown reliable as the per-criterion judge. → The citable origin of
decompose-then-verify — our split-before-classify + per-rule backtest scoring
in one paper. Kin: **ComplexBench** (2407.03978, constraint *composition*
types) and **CFBench** (2408.01122, constraint taxonomy) for compound-rule
splitting.

**The 2026 harness-audit cluster** (via the same graph):
- **"MCP Tool Descriptions Are Smelly!"** (arXiv:2602.14878) — 856 tools
  audited with a 6-component smell rubric: **97.1% have ≥1 smell**; fixing
  descriptions improved success by median **+5.85pp but +67% execution
  steps**, with regressions in 17% of cases. The closest published analog to
  this project (a linter for agent-facing instruction text with measured
  behavioral impact) — and a warning that prescriptions have token/step costs.
- **OpenSkillEval** (arXiv:2605.23657) — audits 30 community skills: skill
  availability ≠ usage; many popular skills **don't outperform base agents**.
  Null-effect artifacts are common → empirical precedent for redundancy
  detection (pairs with ACES's 27% zero/negative lift).
- **ProcCtrlBench** (arXiv:2605.20251) — trajectory-level evaluation:
  normalize heterogeneous logs, apply an 11-type execution-defect ontology,
  score process not outcomes. The closest methodological sibling to our
  condense-then-backtest architecture.
- **SpecBench** (arXiv:2605.21384) — reward hacking measured as the gap
  between visible tests and held-out tests: every frontier agent saturates
  the visible suite while the holdout gap grows **~28pp per 10× code size**.
  → **Goodhart warning for enforcement compilation**: a hook the agent can
  see can be satisfied without honoring the rule — prefer gates that run
  real outcomes (the actual test suite) over pattern proxies, and keep
  matchers out of the agent's sight where possible.
- Supplementary decay numbers: **Multi-IF** (2410.15553, per-turn decay
  0.877→0.707 by turn 3), **CodeIF-Bench** (2503.22688 — repo context and
  growing history degrade coding IF), **LIFBench** (2411.07037 — judge-free
  rubric scoring of IF stability across long contexts).

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

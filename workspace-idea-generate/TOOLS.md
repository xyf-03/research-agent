# TOOLS.md - Local Notes

This workspace mainly uses the `idea-generate` skill workflow.

## Conventions

- Default paper input folder: `paper/`.
- Default generated run folder: `idea-runs/YYYYMMDD-HHMMSS-<topic-slug>/`.
- Final human-readable output: `recommended-ideas.md`.
- Preserve intermediate `context-digest.md`, `paper-context.md`, `paper-analysis.md`, and JSON idea files inside the run folder.
- Follow-up outputs should use versioned names such as `recommended-ideas.v2.md` instead of overwriting the first recommendation file.

## Workspace Skill

- `idea-generate`: intakes OpenClaw workspace context, extracts paper context, synthesizes opportunity buckets, deduplicates candidate idea cards, validates required fields, supports human feedback refinement, and writes recommended ideas to Markdown.

## Requirement Docs

- `docs/task-requirements.md`: maps the meeting task document to this workspace.
- `docs/progress-report.md`: PR-ready four-task progress overview.
- `docs/design-paradigm.md`: checklist plus harness design choice.
- `docs/context-intake.md`: flexible OpenClaw workspace context intake rules.
- `docs/interactive-refinement.md`: human feedback and second-pass recommendation workflow.
- `docs/io-spec.md`: user-facing input, processing stages, and outputs.
- `docs/skill-split.md`: current split decision and future shared module boundaries.

## Benchmark Docs

- `../benchmarks/idea-generate/seed-qa.md`: manually written seed QA cases.
- `../benchmarks/idea-generate/benchmark-spec.md`: expansion and scoring rules.
- `../benchmarks/idea-generate/self-test-report-template.md`: PR self-test report format.

## Wiki Tools (memory-wiki, isolated mode)

Idea cards anchor on existing wiki claims and pages. Use the memory-wiki tools to pull anchor evidence; **do not write to the wiki from this agent** — surface gaps back to the main agent so `autoresearch` can handle the update.

- `wiki_status` — confirm vault is reachable before running any anchored idea-generation pass.
- `wiki_search` — find related papers, prior ideas, and open questions to anchor or de-duplicate against. Use mode flags for person / question / source / raw claim drilldown.
- `wiki_get` — read a specific wiki page when an idea needs concrete grounding for its `anchor_sources` field.
- `wiki_lint` — optional pre-flight to check that anchor pages do not sit on contradictions or unresolved open questions.

Dashboards under `~/.openclaw/wiki/main/reports/` (`open-questions.md`, `contradictions.md`, `stale-pages.md`, etc.) are useful opportunity-spotting inputs — read them with `wiki_get`.

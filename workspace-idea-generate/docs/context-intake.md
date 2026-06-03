# Context Intake

Idea Generate is an OpenClaw workspace agent. It should accept useful research context from the current workspace instead of requiring upstream agents to emit a fixed schema.

## Principle

Use flexible intake at the boundary and stable artifacts inside each run:

```text
OpenClaw workspace materials
  -> context digest
  -> evidence analysis
  -> candidate ideas
  -> recommended-ideas.md
```

Upstream workspaces do not need to change their output format. Idea Generate is responsible for reading the smallest relevant subset and normalizing it into the run directory.

## Intake Priority

Read context in this order:

1. User-provided files, folders, links, or pasted notes.
2. Local `paper/` materials for the current run.
3. Relevant research wiki pages, starting from `/workspace/shared/memory-wiki/index.md` when available.
4. Paper-review outputs, including paper wiki entries, experiment extraction, problem analysis, and validation experiment design.
5. Experiment logs, result tables, ablations, failed attempts, and qualitative observations.
6. Repository files needed to understand implementation boundaries.
7. User preferences, risk tolerance, target venue, compute budget, and follow-up feedback.

Do not bulk-load a full wiki or repository. Prefer topic, domain, metric, dataset, method, and failure keywords from the user request.

## Run Artifacts

For substantial runs, create a run directory under `idea-runs/` and keep normalized context there:

```text
idea-runs/<run-name>/
  brief.md
  context-digest.md
  paper-context.json
  paper-context.md
  paper-analysis.md
  draft-ideas.json
  ideas.dedup.json
  validation.json
  recommended-ideas.md
```

`context-digest.md` should be concise and traceable. It should list:

- task or problem anchor
- source files or pages read
- key paper findings
- relevant experiment results
- known failures or weak evidence
- user constraints and preferences
- assumptions made because context was incomplete

## Compatibility Rules

- Do not require a fixed upstream JSON file.
- Do not modify upstream workspace outputs while generating ideas.
- If relevant context cannot be found, continue with explicit assumptions when possible.
- If there is no research topic or no evidence material at all, ask the user for more context before generating ideas.
- Keep source paths or source names in the evidence chain whenever possible.

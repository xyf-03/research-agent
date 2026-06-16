# 对抗式审查：子Agent输出交付模式

审查日期：2026-06-11
审查范围：全部9个子agent（ingest, curate, extract, critic, design, spec, audit, ideate, judge）

## 规则

子agent的产出只能走两条路之一：
1. **写入 wiki**（通过 `wiki_apply`/`wiki_get` 等 wiki 工具）
2. **直接回复调用者**（返回完整内容到 reply text，由调用者决定后续处理）

**禁止：** 写入自己的 workspace 文件系统，然后让其他 agent 通过路径去找。

## 逐Agent审查

### ingest ✅ 合规

- **产出方式：** `wiki_apply` 创建 paper page + 更新 index + 追加 log
- **文件系统写入：** `raw/sources/` 下的 PDF/txt —— 属于 wiki vault 的 raw source 层，不是"自己的 workspace 输出"
- **结论：** 合规。唯一产物都在 wiki 内。

### curate ✅ 基本合规

- **产出方式：** lint 报告/比较表/查询结果 → 直接回复调用者；lint 日志 → `wiki_apply` 追加
- **AGENTS.md 第51行：** "通过 wiki 工具操作 wiki vault, 不直接读写文件"
- **AGENTS.md 第65行：** "每次 lint 后通过 `wiki_apply` 追加日志条目"
- **结论：** 合规。没有 `outputs/` 路径写入。

### extract ❌ 违规

- **AGENTS.md 第22-24行：** `输出保存到 outputs/{论文简称}/{论文简称}-experiment.md`
- **SKILL.md：** 11节模板，产出写入文件系统
- **main skills/paper-pipeline/SKILL.md 第42行：** `输出到 outputs/{slug}/{slug}-experiment.md`
- **违规性质：** 将产出写入 `workspace/extract/outputs/`，让下游 critic 通过路径找
- **修复方向：** 将完整实验提取文档直接返回到 reply text

### critic ❌ 违规

- **AGENTS.md 第40-42行：** `{论文简称}-problem.md` 保存到 `outputs/{论文简称}/`
- **SKILL.md：** 7节模板，产出写入文件系统
- **main skills/paper-pipeline/SKILL.md 第48行：** `输出到 outputs/{slug}/{slug}-problem.md`
- **违规性质：** 同上，写入 `workspace/critic/outputs/`
- **修复方向：** 将完整问题分析文档直接返回到 reply text

### design ❌ 违规

- **AGENTS.md 第38行：** `输出文件：outputs/{论文简称}/{论文简称}-validation.md`
- **SKILL.md：** 9节模板，产出写入文件系统
- **main skills/paper-pipeline/SKILL.md 第54行：** `输出到 outputs/{slug}/{slug}-validation.md`
- **违规性质：** 写入 `workspace/design/outputs/`
- **修复方向：** 将完整验证实验设计直接返回到 reply text

### spec ❌ 违规

- **AGENTS.md 第26行：** `{论文简称}-codex-prompt.md`
- **AGENTS.md 第56行：** `输出保存到调用方指定的路径，或默认 outputs/{论文简称}/{论文简称}-codex-prompt.md`
- **SKILL.md：** 10节模板，产出写入文件系统
- **main skills/paper-pipeline/SKILL.md 第60行：** `输出到 outputs/{slug}/{slug}-codex-prompt.md`
- **违规性质：** 写入 `workspace/spec/outputs/`
- **修复方向：** 将完整 codex prompt 直接返回到 reply text

### audit ❌ 违规

- **AGENTS.md 第31行：** `{论文简称}-audit.md`
- **AGENTS.md 第66行：** `输出到 outputs/{论文简称}/{论文简称}-audit.md`
- **SKILL.md：** 6节模板，产出写入文件系统
- **main skills/paper-pipeline/SKILL.md 第66行：** `输出到 outputs/{slug}/{slug}-audit.md`
- **违规性质：** 写入 `workspace/audit/outputs/`
- **修复方向：** 将完整审计报告直接返回到 reply text

### ideate ❌ 违规

- **AGENTS.md 第47行：** `Output artifacts go to idea-runs/ or user-specified directories.`
- **SKILL.md 第58行：** `Create a run directory under idea-runs/YYYYMMDD-HHMMSS-<topic-slug>/`
- **SKILL.md 多处：** 写入 `paper-analysis.md`, `draft-ideas.json`, `recommended-ideas.md` 等文件
- **违规性质：** 在 `workspace/ideate/idea-runs/` 创建完整目录树，调用者通过路径找
- **特殊考虑：** ideate 有 Python 脚本（`build_paper_context_pack.py`, `idea_dedup.py`, `validate_idea_cards.py`, `write_idea_markdown.py`），这些脚本依赖中间文件。如果改为纯 inline 返回，脚本链需要重新设计。
- **修复方向：** idea cards 最终产出返回到 reply text；中间脚本产物可保留在临时目录但不作为交付接口

### judge ✅ 合规

- **产出方式：** VERDICT + SCORE + 结构化 Markdown 直接返回到 reply text
- **AGENTS.md 第53-66行：** 明确的输出格式规范（`VERDICT: PASS|FAIL|NEEDS_HUMAN_REVIEW`），全部 inline
- **结论：** 合规。无文件系统产出。

## 汇总

| Agent | 状态 | 违规产出路径 | 修复优先级 |
|-------|------|-------------|-----------|
| ingest | ✅ 合规 | - | - |
| curate | ✅ 合规 | - | - |
| **extract** | ❌ | `outputs/{slug}/{slug}-experiment.md` | P0 |
| **critic** | ❌ | `outputs/{slug}/{slug}-problem.md` | P0 |
| **design** | ❌ | `outputs/{slug}/{slug}-validation.md` | P0 |
| **spec** | ❌ | `outputs/{slug}/{slug}-codex-prompt.md` | P0 |
| **audit** | ❌ | `outputs/{slug}/{slug}-audit.md` | P0 |
| **ideate** | ❌ | `idea-runs/YYYYMMDD-HHMMSS-<slug>/` | P1（脚本依赖复杂） |
| judge | ✅ 合规 | - | - |

**违规率：6/9 = 67%**

## 对抗性质疑与回应

### 质疑1："outputs/ 路径是 main agent 指定的，不算子agent自己决定"

**回应：** 即使路径由调用者指定，子agent的 AGENTS.md 和 SKILL.md 里硬编码了默认 `outputs/{slug}/` 路径。子agent被设计为"把产出写到文件，然后告诉调用者路径"。这违反了规则——无论路径谁指定，都不应该写入文件系统让其他agent找。

### 质疑2："大文档（几百行 Markdown）返回 inline 会撑爆上下文"

**回应：** `sessions_spawn(mode: "run")` 的返回值就是子agent的最终 reply text，已经在调用者的上下文里。写入文件再读回来反而多一次 I/O。如果担心上下文，应该裁剪而非引入文件系统耦合。

### 质疑3："ideate 的 Python 脚本链需要中间文件，不能纯 inline"

**回应：** 这是唯一有效的质疑。ideate 的脚本（dedup、validate、write markdown）需要读前一步的 JSON 输出。但最终 `recommended-ideas.md` 仍应返回到 reply text，而非让调用者去 `idea-runs/` 找。中间脚本产物可以在临时目录，这不暴露给调用者作为接口。

### 质疑4："下游 stage 需要上游的完整产出，不写文件怎么传？"

**回应：** main agent 拿到上游的 reply text 后，直接把它嵌入下游的 task 参数里。不要传文件路径或 session key；下游 stage 需要的完整上下文应作为 task 内容传递。

## 修复计划

### 阶段1：P0 修复（extract, critic, design, spec, audit）

每个 agent 改3处：
1. **AGENTS.md** — 输出描述改为 "直接回复调用者，包含完整产出文档（Markdown）"
2. **SKILL.md** — 输出模板保留，但去掉"保存到 outputs/" 指令，改为 "在回复中直接输出以下结构"
3. **Main skills** — paper-pipeline 的 SKILL.md 去掉 `输出到 outputs/{slug}/` 参数，改为期望 inline 回复

### 阶段2：P1 修复（ideate）

- AGENTS.md: 改为 "返回 recommended-ideas.md 完整内容到 reply text"
- SKILL.md: 保留脚本中间产物在临时目录，最终 Markdown 在 reply 中返回
- brainstorm SKILL.md: 改为期望 inline 回复

### 阶段3：清理

- 删除各 agent workspace 下遗留的 `outputs/` 和 `idea-runs/` 目录（如有）

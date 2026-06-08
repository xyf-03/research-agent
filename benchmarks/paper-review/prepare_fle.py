#!/usr/bin/env python3
"""Prepare Focus-Level Eval benchmark materials for paper-review S3 evaluation.

Reads annotation_result.csv (the FLE dataset), selects papers with sufficient
human-annotated weaknesses, downloads paper PDFs from OpenReview and extracts
full text as S3 input, then generates:
  1. materials/fle/{paper_id}_fulltext.md  -- extracted paper text (S3 input)
  2. fle_qa.json                            -- QA items with judge: agent

Usage:
  python3 benchmarks/paper-review/prepare_fle.py                    # default: 5 papers
  python3 benchmarks/paper-review/prepare_fle.py --papers 10        # select 10 papers
  python3 benchmarks/paper-review/prepare_fle.py --dry-run          # preview only
  python3 benchmarks/paper-review/prepare_fle.py --no-download      # skip PDF download
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
MATERIALS_FLE = HERE / "materials" / "fle"
FLE_CSV = HERE / "annotation_result.csv"
FLE_QA_PATH = HERE / "fle_qa.json"

MIN_WEAKNESSES = 3
MAX_TEXT_CHARS = 15000  # ~ first 5-7 pages of a typical paper


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

def load_fle_csv(csv_path: Path) -> list[dict]:
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            parsed = {
                "paper_id": row["paper_id"],
                "paper_title": row["paper_title"],
                "venue": row["venue"],
                "year": row["year"],
                "open_review_url": row.get("open_review_url", ""),
                "expert_review": row.get("expert_review", ""),
            }
            for field in ("expert_weakness_items", "expert_weakness_target_annotation",
                          "expert_weakness_aspect_annotation"):
                try:
                    parsed[field] = json.loads(row.get(field, "[]"))
                except (json.JSONDecodeError, TypeError):
                    parsed[field] = []
            rows.append(parsed)
    return rows


# ---------------------------------------------------------------------------
# PDF download + text extraction
# ---------------------------------------------------------------------------

def download_pdf(paper_id: str, cache_dir: Optional[Path] = None) -> Optional[bytes]:
    """Download paper PDF from OpenReview. Caches to disk."""
    cache = cache_dir or MATERIALS_FLE / ".pdf_cache"
    cache.mkdir(parents=True, exist_ok=True)
    pdf_path = cache / f"{paper_id}.pdf"

    if pdf_path.exists():
        return pdf_path.read_bytes()

    url = f"https://openreview.net/pdf?id={paper_id}"
    try:
        import requests
        resp = requests.get(url, timeout=60,
                            headers={"User-Agent": "Mozilla/5.0 (research-benchmark)"})
        resp.raise_for_status()
        pdf_path.write_bytes(resp.content)
        return resp.content
    except Exception as e:
        print(f"  [WARN] PDF download failed for {paper_id}: {e}", file=sys.stderr)
        return None


def extract_text_from_pdf(pdf_bytes: bytes, max_chars: int = MAX_TEXT_CHARS) -> str:
    """Extract text from PDF bytes using PyMuPDF. Returns first max_chars chars."""
    try:
        import fitz
    except ImportError:
        print("  [WARN] PyMuPDF not available, install with: pip install PyMuPDF",
              file=sys.stderr)
        return ""

    doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
    text_parts = []
    total = 0
    for page in doc:
        page_text = page.get_text()
        text_parts.append(page_text)
        total += len(page_text)
        if total >= max_chars:
            break
    doc.close()

    full_text = "\n".join(text_parts)
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n\n... (truncated)"
    return full_text


# ---------------------------------------------------------------------------
# Paper selection
# ---------------------------------------------------------------------------

def select_papers(rows: list[dict], max_papers: int = 5) -> list[dict]:
    candidates = [r for r in rows if len(r["expert_weakness_items"]) >= MIN_WEAKNESSES]
    candidates.sort(key=lambda r: (-len(r["expert_weakness_items"]), r["paper_id"]))
    selected = candidates[:max_papers]
    n_weak = [len(r["expert_weakness_items"]) for r in selected]
    print(f"[prepare_fle] Selected {len(selected)} papers "
          f"(weakness range: {min(n_weak)}-{max(n_weak)}, "
          f"out of {len(candidates)} with >= {MIN_WEAKNESSES} weaknesses)")
    return selected


# ---------------------------------------------------------------------------
# Material generation
# ---------------------------------------------------------------------------

def generate_materials(selected: list[dict], dry_run: bool = False,
                       download: bool = True) -> dict[str, str]:
    """Generate material files. Returns {paper_id: full_text_str} for QA generation."""
    MATERIALS_FLE.mkdir(parents=True, exist_ok=True)
    full_texts = {}

    for i, paper in enumerate(selected):
        pid = paper["paper_id"]
        print(f"[prepare_fle] [{i+1}/{len(selected)}] {pid}: {paper['paper_title'][:60]}")

        # ---- Get full paper text ----
        full_text = ""
        if download:
            pdf_bytes = download_pdf(pid)
            if pdf_bytes:
                full_text = extract_text_from_pdf(pdf_bytes)
                print(f"  PDF: {len(pdf_bytes)} bytes -> {len(full_text)} chars extracted")
            else:
                print(f"  PDF: download failed, falling back to abstract")
            time.sleep(2)  # rate limit

        # Fallback: use OpenReview API abstract + expert review summary
        if not full_text:
            abstract = _fetch_abstract(pid, paper)
            expert_summary = _extract_expert_summary(paper["expert_review"])
            full_text = (
                f"# {paper['paper_title']}\n\n"
                f"## Abstract\n{abstract}\n\n"
                f"## Expert Reviewer Summary\n{expert_summary}\n"
            )

        # ---- Write full text ----
        text_path = MATERIALS_FLE / f"{pid}_fulltext.md"
        if not dry_run:
            text_path.write_text(full_text, encoding="utf-8")
        full_texts[pid] = full_text

        # ---- Write weaknesses as gold_answer ----
        weaknesses = paper["expert_weakness_items"]
        targets = paper["expert_weakness_target_annotation"]
        aspects = paper["expert_weakness_aspect_annotation"]
        weakness_list = []
        for j, (w, t, a) in enumerate(zip(weaknesses, targets, aspects)):
            weakness_list.append({
                "id": f"W{j+1}",
                "text": _clean_weakness(w),
                "target": t,
                "aspect": a,
            })

        gold = {
            "paper_id": pid,
            "paper_title": paper["paper_title"],
            "num_weaknesses": len(weakness_list),
            "human_weaknesses": weakness_list,
        }
        gold_path = MATERIALS_FLE / f"{pid}_weaknesses.json"
        if not dry_run:
            gold_path.write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")

    return full_texts


def _fetch_abstract(paper_id: str, paper: dict) -> str:
    """Fetch official abstract from OpenReview API."""
    try:
        import requests
        resp = requests.get(
            f"https://api.openreview.net/notes?forum={paper_id}&limit=50",
            timeout=15)
        for note in resp.json().get("notes", []):
            if "Submission" in note.get("invitation", ""):
                content = note.get("content", {})
                if isinstance(content, dict):
                    abstract = content.get("abstract", "")
                    if abstract:
                        return str(abstract)[:2000]
    except Exception:
        pass
    return "(未能获取摘要)"


def _extract_expert_summary(expert_review: str) -> str:
    """Extract Summary section from expert review, excluding Strengths/Weaknesses."""
    if not expert_review:
        return "(未提供)"
    parts = re.split(r'\n##\s*(?:Strengths|Weaknesses)', expert_review, maxsplit=1)
    summary = re.sub(r'^##\s*Summary[^\n]*\n*', '', parts[0].strip(),
                     flags=re.IGNORECASE).strip()
    if not summary:
        # Try strengths as fallback (they describe the paper without giving away answers)
        m = re.search(r'##\s*Strengths[^\n]*\n(.*?)(?=\n##\s|\Z)',
                      expert_review, re.DOTALL | re.IGNORECASE)
        if m:
            summary = "(Summary unavailable; strengths provided as context)\n\n" + m.group(1)[:500]
    return summary if summary else "(未提供)"


def _clean_weakness(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^[\-\*]\s*\*?\*?', '', text)
    text = re.sub(r'\*$', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ---------------------------------------------------------------------------
# fle_qa.json generation
# ---------------------------------------------------------------------------

def generate_fle_qa(selected: list[dict], dry_run: bool = False) -> None:
    """Generate fle_qa.json. input_material references material file paths
    (paper text lives in materials/fle/, not inlined in qa.jsonl)."""
    items = []
    for i, paper in enumerate(selected):
        pid = paper["paper_id"]

        gold_path = MATERIALS_FLE / f"{pid}_weaknesses.json"
        if gold_path.exists():
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
        else:
            gold = {"human_weaknesses": []}

        weakness_texts = [w["text"] for w in gold.get("human_weaknesses", [])]
        target_types = sorted(set(
            w["target"] for w in gold.get("human_weaknesses", []) if w["target"]))
        aspect_types = sorted(set(
            w["aspect"] for w in gold.get("human_weaknesses", []) if w["aspect"]))

        # Reference the material file path — follow existing convention:
        # seed QA items use "benchmark/materials/filename"
        material_path = f"benchmark/materials/fle/{pid}_fulltext.md"

        item = {
            "qa_id": f"fle-{i+1:03d}",
            "agent": "main",
            "skill": "problem-analyzer",
            "task_type": "s3-quality-fle",
            "input_material": (
                f"请阅读 {material_path} 中的论文全文，然后对该论文进行审稿式问题分析。\n\n"
                f"论文标题：{paper['paper_title']}\n"
                f"会议：{paper['venue']} {paper['year']}\n"
                f"OpenReview：{paper['open_review_url']}\n\n"
                f"请基于论文内容，执行 paper-review-style-problem-analyzer skill，"
                f"对论文的方法机制、实验支撑、贡献声明进行审稿式质疑，"
                f"发现潜在问题、排序优先级、提炼研究空缺，"
                f"输出完整的 6 个 section 问题分析文档。"
            ),
            "question": (
                f"请执行 paper-review-style-problem-analyzer skill，"
                f"对论文「{paper['paper_title']}」({paper['venue']} {paper['year']})"
                f"进行审稿式问题分析。请严格按 skill 模板输出完整的6个section："
                f"文档定位 / 方法机制与关键前提 / 核心贡献声明与审稿式质疑 / "
                f"潜在问题分析 / 验证候选问题与优先级 / 研究空缺方向与简短结论。"
            ),
            "expected_artifacts": [
                f"workspace-paper-review/outputs/bench-<run>/fle-{i+1:03d}.md"
            ],
            "gold_answer": {
                "paper_title": paper["paper_title"],
                "human_weaknesses": weakness_texts,
                "target_types": target_types,
                "aspect_types": aspect_types,
            },
            "rubric": (
                "你是一个严格的评测者。请对比 agent 输出的问题分析（CANDIDATE）和人类审稿人标注的 weakness 列表（REFERENCE），从以下维度打分：\n\n"
                "1. **召回率 (Recall - 40%)**：REFERENCE 中的每条人类审稿 weakness，CANDIDATE 是否发现（语义覆盖）？"
                "逐条判断：完全命中 / 部分命中 / 遗漏。计算 |命中| / |REFERENCE总数|。\n"
                "2. **准确率 (Precision - 40%)**：CANDIDATE 中的每个问题是否真实有效？"
                "逐条判断：明确有效 / 部分有效 / 无效或过度推断。计算 |有效| / |CANDIDATE总数|。\n"
                "3. **质疑类型覆盖 (Target/Aspect - 20%)**：CANDIDATE 发现的问题是否覆盖了 REFERENCE 中的"
                f" target 维度（{', '.join(target_types)}）和 aspect 维度（{', '.join(aspect_types)}）？\n\n"
                "综合评分 = 0.4 × Recall + 0.4 × Precision + 0.2 × 类型覆盖。\n\n"
                "输出 JSON：{\"score\": <0-1>, \"rationale\": \"<召回X/Y，准确X/Y，覆盖X/Y>\"}"
            ),
            "rubric_dimensions": ["recall", "precision", "target_aspect_match"],
            "pass_threshold": 0.5,
            "judge": "agent",
            "weight": 1.0,
        }
        items.append(item)

    if not dry_run:
        FLE_QA_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[prepare_fle] Generated {FLE_QA_PATH} with {len(items)} QA items")
    else:
        print(f"[prepare_fle] [dry-run] Would generate {FLE_QA_PATH} with {len(items)} QA items")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Prepare Focus-Level Eval benchmark materials for paper-review S3")
    parser.add_argument("--papers", type=int, default=5)
    parser.add_argument("--no-download", action="store_true",
                        help="Skip PDF download (use abstract fallback)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not FLE_CSV.exists():
        print(f"[prepare_fle] ERROR: {FLE_CSV} not found.", file=sys.stderr)
        return 1

    rows = load_fle_csv(FLE_CSV)
    print(f"[prepare_fle] Loaded {len(rows)} papers from {FLE_CSV}")

    selected = select_papers(rows, max_papers=args.papers)
    if not selected:
        print("[prepare_fle] ERROR: No papers meet criteria", file=sys.stderr)
        return 1

    full_texts = generate_materials(selected, dry_run=args.dry_run,
                                    download=not args.no_download)
    generate_fle_qa(selected, dry_run=args.dry_run)

    if not args.dry_run:
        print(f"\n[prepare_fle] Done. Next: python benchmarks/paper-review/build_qa.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

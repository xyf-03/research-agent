#!/usr/bin/env python3
"""
Expand 8 seed QAs into a larger benchmark using LLM-generated variants.

Dimensions of expansion:
1. Switch papers:       replace paper content with a different paper
2. Rephrase:            reword the question while keeping meaning
3. Change input format: vary input format (markdown, plain text, bullet points)
4. Boundary cases:      test edge conditions (empty input, very long input, etc.)
5. Error injection:     introduce deliberate errors in input to test robustness

Output: full_benchmark.json (seed QAs + expanded variants)
"""

import json
import sys
from pathlib import Path
from config import (
    chat_llm, load_seed_qa, save_json,
    FULL_BENCHMARK_FILE, BENCHMARK_DIR,
)

EXPAND_SYSTEM = """You are a QA test-case generator for an academic paper review agent.
Your job: given seed QA pairs as few-shot examples, generate DIVERSE variant test cases.

The agent under test is a 5-stage paper-review pipeline:
1. wiki-organizer:      extracts structured Wiki from raw paper text
2. experiment-extractor: deep extraction of experiment details
3. problem-analyzer:    reviewer-style critical analysis
4. validation-designer: designs verification experiments based on analysis
5. codex-prompt-generator: generates Codex CLI prompts for experiments

Variant dimensions to cover:
- Switch papers: change the paper content (different ML domain OK)
- Rephrase: reword the question while keeping the same capability under test
- Change input format: vary between markdown, plain text, structured JSON, bullet lists
- Boundary cases: very short input (1 sentence), very long input, mixed languages
- Error injection: incomplete data, contradictory statements, missing sections

Requirements for generated QA:
- Each must have: id, capability, skill, title, input_material, question, standard_answer
- standard_answer must include: structure, fields, must_contain, key_behavior
- The standard_answer must be CORRECT (you are the oracle)
- Make variants clearly different from seeds, not cosmetic changes
- Each variant should test the SAME capability but in a DIFFERENT way

Return ONLY valid JSON: { "test_cases": [ ... ] }"""


def build_expansion_prompt(seed_qa: list, target_count: int = 18) -> str:
    seeds_json = json.dumps(seed_qa, ensure_ascii=False, indent=2)
    return f"""Below are {len(seed_qa)} seed QA pairs. Generate {target_count} additional test cases
covering ALL 5 expansion dimensions evenly.

Think about:
- At least 3 cases with different papers (GAN, NLP, RL, CV other than CIFAR)
- At least 4 cases with rephrased questions
- At least 2 cases with non-markdown input formats
- At least 4 boundary/edge cases
- At least 3 error-injection cases

The capability tags are: wiki-extraction, experiment-extraction, problem-analysis,
validation-design, codex-generation, error-handling, stage-boundary, multi-paper-comparison

Seed QA pairs (use as reference for format and quality):
{seeds_json}

Generate {target_count} new test cases. Return ONLY the JSON object with key "test_cases"."""


def expand_benchmark(target_count: int = 18, dry_run: bool = False):
    seed_qa = load_seed_qa()
    print(f"Loaded {len(seed_qa)} seed QA pairs")

    prompt = build_expansion_prompt(seed_qa, target_count)
    print(f"Expansion prompt: {len(prompt)} chars")

    if dry_run:
        print("[DRY RUN] Would call LLM with expansion prompt")
        print(f"[DRY RUN] Prompt preview:\n{prompt[:500]}...")
        return

    print("Calling DeepSeek to generate variants...")
    response = chat_llm(EXPAND_SYSTEM, prompt, timeout=300, max_tokens=16384)
    print(f"LLM response: {len(response)} chars")

    # Extract JSON from response (may be wrapped in ```json blocks)
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        response = "\n".join(lines)

    try:
        data = json.loads(response)
        new_cases = data.get("test_cases", [])
    except json.JSONDecodeError as e:
        print(f"ERROR parsing LLM response: {e}")
        print(f"Response:\n{response[:1000]}")
        sys.exit(1)

    if len(new_cases) < target_count:
        print(f"WARNING: requested {target_count} but got {len(new_cases)} cases")

    # Build full benchmark: seeds + expanded
    full_benchmark = list(seed_qa) + new_cases
    print(f"Total benchmark size: {len(full_benchmark)} ({len(seed_qa)} seeds + {len(new_cases)} expanded)")

    # Count by dimension
    capabilities = {}
    for tc in full_benchmark:
        cap = tc.get("capability", "unknown")
        capabilities[cap] = capabilities.get(cap, 0) + 1
    print("Capability distribution:")
    for cap, count in sorted(capabilities.items()):
        print(f"  {cap}: {count}")

    save_json(full_benchmark, FULL_BENCHMARK_FILE)
    print(f"Saved to {FULL_BENCHMARK_FILE}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Expand benchmark via LLM")
    parser.add_argument("--count", type=int, default=18, help="Number of new cases to generate")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt without calling LLM")
    args = parser.parse_args()
    expand_benchmark(target_count=args.count, dry_run=args.dry_run)

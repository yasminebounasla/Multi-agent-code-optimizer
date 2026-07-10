"""
Explainer agent.

Given the original code and one optimized candidate (plus optional
empirical timing data from analyze_complexity.py), asks the LLM to
produce a structured, complexity-focused justification of *why* the
optimized version is faster.

This is intentionally separate from the Optimizer's own "explanation"
field: the Optimizer explains its own reasoning while proposing a fix
(can be biased / hand-wavy), while the Explainer acts as an independent
reviewer that must justify speed purely in terms of algorithmic
complexity (Big-O), grounded in the actual code diff and, if available,
the measured slope from analyze_complexity.py.
"""
from __future__ import annotations  # allows list[dict] | None on Python 3.9

from llm_client import ask_llm_json

EXPLAINER_SYSTEM_PROMPT = """You are a senior algorithms reviewer.
You will be given the ORIGINAL code and an OPTIMIZED candidate that is
claimed to be faster. Your job is to justify — in terms of algorithmic
complexity — whether and why the optimized version is actually faster.

Rules:
- Identify the time complexity (Big-O) of the ORIGINAL code.
- Identify the time complexity (Big-O) of the OPTIMIZED code.
- Explain the specific mechanism causing the improvement (e.g. list
  membership check O(n) replaced by set/dict membership check O(1),
  redundant recomputation removed, nested loop collapsed, etc.).
- If empirical measured data (timings across input sizes) is provided,
  state whether it is consistent with your complexity analysis.
- If the optimized code is NOT actually better (same complexity, or
  only a constant-factor speedup, or complexity is worse in some
  case), say so honestly. Do not inflate the improvement.
- Be precise and concise. No marketing language.

Return ONLY valid JSON (no markdown fences, no triple-quoted strings —
escape newlines in code/text fields as \\n) matching this schema:
{
  "original_complexity": "string, e.g. O(n^2)",
  "optimized_complexity": "string, e.g. O(n)",
  "mechanism": "string, plain-English explanation of the specific code-level reason for the speedup",
  "consistent_with_measurements": true/false/null,
  "measurement_note": "string or null, only if measurement data was provided",
  "verdict": "genuine_improvement" | "constant_factor_only" | "no_improvement" | "worse_in_some_cases",
  "confidence": "high" | "medium" | "low"
}
"""


def explain_optimization(
    original_code: str,
    optimized_code: str,
    strategy_name: str = "",
    measured_data: list[dict] | None = None,
) -> dict:
    """
    Args:
        original_code: the baseline source code.
        optimized_code: the candidate optimized source code.
        strategy_name: optional label for the strategy (for readability in logs).
        measured_data: optional list of {"n": int, "time_original": float,
            "time_optimized": float} points from analyze_complexity.py,
            used to cross-check the complexity claim empirically.

    Returns:
        dict matching EXPLAINER_SYSTEM_PROMPT's JSON schema.
    """
    measurement_block = ""
    if measured_data:
        rows = "\n".join(
            f"  n={d['n']}: original={d['time_original']:.6f}s, "
            f"optimized={d['time_optimized']:.6f}s"
            for d in measured_data
        )
        measurement_block = f"\n\nMEASURED TIMINGS:\n{rows}"

    user_prompt = f"""STRATEGY NAME: {strategy_name or "(unnamed)"}

ORIGINAL CODE:
{original_code}

OPTIMIZED CODE:
{optimized_code}{measurement_block}

Analyze and return the JSON verdict as specified."""

    return ask_llm_json(EXPLAINER_SYSTEM_PROMPT, user_prompt)


def explain_all(
    original_code: str,
    candidates: list[dict],
    measured_data_by_name: dict[str, list[dict]] | None = None,
) -> list[dict]:
    """
    Batch helper: runs explain_optimization for a list of candidates.

    Args:
        original_code: baseline source.
        candidates: list of {"name": str, "code": str} dicts (e.g. the
            strategies produced by the Optimizer).
        measured_data_by_name: optional dict mapping strategy name ->
            measured_data list (see explain_optimization).

    Returns:
        list of dicts, each = candidate info merged with its explanation,
        e.g. {"name": ..., "code": ..., "explanation": {...}}
    """
    results = []
    measured_data_by_name = measured_data_by_name or {}
    for candidate in candidates:
        name = candidate.get("name", "")
        code = candidate["code"]
        explanation = explain_optimization(
            original_code=original_code,
            optimized_code=code,
            strategy_name=name,
            measured_data=measured_data_by_name.get(name),
        )
        results.append({"name": name, "code": code, "explanation": explanation})
    return results
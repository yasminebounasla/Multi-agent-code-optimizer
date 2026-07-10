"""
Scorer agent.

Replaces a simple pass/fail gate with a composite score across three
axes: speed, risk, and readability. Speed is computed directly from
empirical timings (no LLM needed, deterministic and cheap). Risk and
readability are judged by the LLM, since they require reading the code
(e.g. does the optimization silently change behavior on edge cases,
does it rely on fragile assumptions, is it still maintainable).

The final composite score is a weighted sum, so callers can rank
multiple candidate strategies instead of just discarding "failed" ones.
"""
from __future__ import annotations  # allows dict | None on Python 3.9

import math

from llm_client import ask_llm_json

SCORER_SYSTEM_PROMPT = """You are a strict senior code reviewer.
You will be given ORIGINAL code and an OPTIMIZED candidate. Score the
optimized candidate on two axes, each from 0 to 10:

1. "risk" — how likely is this change to introduce a behavioral bug,
   regression, or edge-case failure versus the original?
   0 = clearly behavior-preserving and safe.
   10 = very likely to break correctness (e.g. changes ordering,
   drops duplicates unintentionally, changes numeric precision,
   mishandles empty input, silently changes semantics).
   NOTE: higher risk = worse. This will be inverted later, just score
   the actual risk level honestly.

2. "readability" — how readable/maintainable is the optimized code
   compared to idiomatic style for this language?
   0 = obfuscated, clever-but-cryptic, hard to maintain.
   10 = clear, idiomatic, as easy or easier to read than the original.

Also give a one-sentence justification for each score.

Return ONLY valid JSON (no markdown fences, no triple-quoted strings —
escape newlines as \\n) matching this schema:
{
  "risk_score": number (0-10),
  "risk_justification": "string",
  "readability_score": number (0-10),
  "readability_justification": "string"
}
"""

# Default weights for the composite score. Must sum to 1.0.
DEFAULT_WEIGHTS = {
    "speed": 0.5,
    "risk": 0.3,
    "readability": 0.2,
}


def _speed_score(time_original: float, time_optimized: float) -> float:
    """
    Deterministic speed score in [0, 10] based on measured speedup ratio.
    0 = no improvement or slower. 10 = huge speedup (>=50x).
    Uses a log scale so a 2x speedup and a 50x speedup are both
    meaningfully distinguished instead of saturating instantly.
    """
    if time_optimized <= 0 or time_original <= 0:
        return 0.0
    speedup = time_original / time_optimized
    if speedup <= 1.0:
        return 0.0
    score = (math.log2(speedup) / math.log2(50)) * 10
    return max(0.0, min(10.0, score))


def score_candidate(
    original_code: str,
    optimized_code: str,
    time_original: float,
    time_optimized: float,
    weights: dict | None = None,
    strategy_name: str = "",
) -> dict:
    """
    Produces a composite score for one optimization candidate.

    Args:
        original_code / optimized_code: source snippets.
        time_original / time_optimized: benchmark timings in seconds
            (e.g. from the profiler or analyze_complexity.py, at a
            representative input size).
        weights: optional override of DEFAULT_WEIGHTS.
        strategy_name: optional label for logging.

    Returns:
        {
          "name": str,
          "speed_score": float,
          "risk_score": float,
          "readability_score": float,
          "composite_score": float,   # 0-10, higher = better overall
          "risk_justification": str,
          "readability_justification": str,
          "recommendation": "adopt" | "review" | "reject"
        }
    """
    weights = weights or DEFAULT_WEIGHTS

    speed = _speed_score(time_original, time_optimized)

    user_prompt = f"""STRATEGY NAME: {strategy_name or "(unnamed)"}

ORIGINAL CODE:
{original_code}

OPTIMIZED CODE:
{optimized_code}

Score risk and readability as specified."""

    llm_result = ask_llm_json(SCORER_SYSTEM_PROMPT, user_prompt)
    risk = float(llm_result["risk_score"])
    readability = float(llm_result["readability_score"])

    # Risk is inverted: low risk contributes positively to the composite.
    inverted_risk = 10 - risk

    composite = (
        weights["speed"] * speed
        + weights["risk"] * inverted_risk
        + weights["readability"] * readability
    )

    if risk >= 7:
        recommendation = "reject"
    elif composite >= 7:
        recommendation = "adopt"
    else:
        recommendation = "review"

    return {
        "name": strategy_name,
        "speed_score": round(speed, 2),
        "risk_score": round(risk, 2),
        "readability_score": round(readability, 2),
        "composite_score": round(composite, 2),
        "risk_justification": llm_result.get("risk_justification", ""),
        "readability_justification": llm_result.get("readability_justification", ""),
        "recommendation": recommendation,
    }


def score_all(
    original_code: str,
    candidates: list[dict],
    weights: dict | None = None,
) -> list[dict]:
    """
    Batch helper: scores multiple candidates and returns them sorted by
    composite_score descending, so the best candidate is first.

    Args:
        candidates: list of dicts, each must have:
            "name": str, "code": str,
            "time_original": float, "time_optimized": float

    Returns:
        list of score_candidate() results, sorted best-first.
    """
    results = [
        score_candidate(
            original_code=original_code,
            optimized_code=c["code"],
            time_original=c["time_original"],
            time_optimized=c["time_optimized"],
            weights=weights,
            strategy_name=c.get("name", ""),
        )
        for c in candidates
    ]
    return sorted(results, key=lambda r: r["composite_score"], reverse=True)
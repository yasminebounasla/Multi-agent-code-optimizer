"""
Test script: verifies the fallback retry loop actually works.

Updated for the current pipeline: the Orchestrator now tries multi-strategy
FIRST (generate_strategies). This test forces that first attempt to fail
entirely (2 broken strategies), so the Orchestrator falls back to the
single-strategy retry loop -- which is what we're actually testing here.

This does NOT call the real LLM at all (everything is mocked), so it's
safe to run without burning API tokens.

Run with: python test_retry_loop.py
"""

from unittest.mock import patch
import orchestrator

# --- Round 1 (multi-strategy attempt): force BOTH candidates to be broken ---
BROKEN_CODE_A = """
def run(n: int):
    return []  # deliberately wrong: always returns empty list
"""

BROKEN_CODE_B = """
def run(n: int):
    return [0]  # deliberately wrong: always returns [0]
"""

FAKE_STRATEGIES = [
    {"name": "Broken A", "explanation": "fake broken strategy 1", "code": BROKEN_CODE_A},
    {"name": "Broken B", "explanation": "fake broken strategy 2", "code": BROKEN_CODE_B},
]

# --- Fallback retry loop: round 2 (still broken) -> round 3 (fixed) ---
FIXED_CODE = """
def run(n: int):
    data = [i % (n // 2) for i in range(n)]
    seen = set()
    duplicates = set()
    for num in data:
        if num in seen:
            duplicates.add(num)
        seen.add(num)
    return sorted(duplicates)
"""

retry_call_count = {"n": 0}


def fake_optimize_code(original_code, profiler_report, feedback=None):
    retry_call_count["n"] += 1
    if retry_call_count["n"] == 1:
        print(">> [TEST] Retry round 2: still broken (on purpose)")
        return {"explanation": "Fake retry round 2 (still broken)", "code": BROKEN_CODE_A}
    else:
        print(f">> [TEST] Retry round {retry_call_count['n'] + 1}: received feedback -> {feedback}")
        print(">> [TEST] Returning FIXED code now")
        return {"explanation": "Fake retry round (fixed)", "code": FIXED_CODE}


FAKE_EXPLANATION = {
    "original_complexity": "O(n^2)", "optimized_complexity": "O(n)",
    "mechanism": "set-based lookup", "consistent_with_measurements": True,
    "measurement_note": None, "verdict": "genuine_improvement", "confidence": "high",
}

FAKE_SCORE = {
    "name": "retry", "speed_score": 10.0, "risk_score": 0.0, "readability_score": 9.0,
    "composite_score": 9.7, "risk_justification": "safe", "readability_justification": "clean",
    "recommendation": "adopt",
}


if __name__ == "__main__":
    with patch("orchestrator.generate_strategies", return_value=FAKE_STRATEGIES), \
         patch("orchestrator.optimize_code", side_effect=fake_optimize_code), \
         patch("orchestrator.explain_optimization", return_value=FAKE_EXPLANATION), \
         patch("orchestrator.score_candidate", return_value=FAKE_SCORE):
        result = orchestrator.run_pipeline("examples/slow_example_1.py", (2000,))

    print("\n=== TEST RESULT ===")
    print(f"Succeeded: {result['success']}")
    print(f"Rounds needed: {result['rounds']}")

    assert retry_call_count["n"] == 2, "Expected exactly 2 calls to the single-strategy optimizer (1 fail + 1 success)"
    assert result["success"] is True, "Pipeline should have succeeded via the fallback retry loop"
    assert result["rounds"] == 3, "Should have needed round 3 (multi-strategy=round1 failed, retry round2 failed, retry round3 succeeded)"
    print("\n✅ Fallback retry loop confirmed working: multi-strategy failed -> "
          "single-strategy retry round 2 failed -> round 3 succeeded with feedback")
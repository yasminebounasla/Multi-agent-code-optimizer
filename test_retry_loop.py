"""
Test script: verifies the retry loop actually works by forcing the
Optimizer to produce BROKEN code on round 1, then correct code on round 2.

This does NOT touch your real optimizer.py / benchmarker.py — it just
temporarily replaces optimize_code() with a fake version for this test.

Run with: python test_retry_loop.py
"""

from unittest.mock import patch
from agents.profiler import profile_code
import orchestrator

# Round 1: intentionally broken code (missing the seen check -> wrong output)
BROKEN_CODE = """
def run(n: int):
    data = [i % (n // 2) for i in range(n)]
    return []  # deliberately wrong: always returns empty list
"""

# Round 2: correct optimized code
FIXED_CODE = """
def run(n: int):
    data = [i % (n // 2) for i in range(n)]
    seen = set()
    duplicates = set()
    for num in data:
        if num in seen:
            duplicates.add(num)
        seen.add(num)
    return sorted(list(duplicates))
"""

call_count = {"n": 0}


def fake_optimize_code(original_code, profiler_report, feedback=None):
    call_count["n"] += 1
    if call_count["n"] == 1:
        print(">> [TEST] Returning BROKEN code on round 1 (on purpose)")
        return {"explanation": "Fake round 1 (broken on purpose)", "code": BROKEN_CODE}
    else:
        print(f">> [TEST] Round {call_count['n']}: received feedback -> {feedback}")
        print(">> [TEST] Returning FIXED code now")
        return {"explanation": "Fake round 2 (fixed)", "code": FIXED_CODE}


if __name__ == "__main__":
    with patch("orchestrator.optimize_code", side_effect=fake_optimize_code):
        result = orchestrator.run_pipeline("examples/slow_example_1.py", (2000,))

    print("\n=== TEST RESULT ===")
    print(f"Succeeded: {result['success']}")
    print(f"Rounds needed: {result['rounds']}")

    assert call_count["n"] == 2, "Expected exactly 2 calls to the optimizer (1 fail + 1 success)"
    assert result["success"] is True, "Pipeline should have succeeded on round 2"
    print("\n✅ Retry loop confirmed working: failed round 1 -> fed back -> succeeded round 2")
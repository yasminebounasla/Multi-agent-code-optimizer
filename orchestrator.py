"""
Orchestrator
Wires the three agents together into the multi-strategy pipeline:

    Profiler -> Optimizer (N strategies) -> Benchmarker (tests all, keeps best)
                                                    |
                                    if none pass -> single-strategy retry loop
                                                    (up to MAX_ROUNDS, using feedback)

Run with: python orchestrator.py examples/slow_example_1.py
"""

import sys
import json

from agents.profiler import profile_code
from agents.optimizer import optimize_code, generate_strategies
from agents.benchmarker import benchmark, benchmark_multiple

MAX_ROUNDS = 3
NUM_STRATEGIES = 3


def run_pipeline(filepath: str, args: tuple = ()):
    with open(filepath, "r") as f:
        original_code = f.read()

    print(f"\n=== PROFILER: analyzing {filepath} ===")
    profiler_report = profile_code(filepath, args)
    print(f"Baseline time: {profiler_report['baseline_time']}s")
    print(f"Top bottlenecks: {profiler_report['bottlenecks']}\n")

    # --- Round 1: multi-strategy attempt ---
    print(f"=== ROUND 1: OPTIMIZER (proposing {NUM_STRATEGIES} strategies) ===")
    strategies = generate_strategies(original_code, profiler_report, NUM_STRATEGIES)
    for s in strategies:
        print(f"  - {s['name']}: {s['explanation']}")

    print(f"\n=== ROUND 1: BENCHMARKER (testing all {len(strategies)} strategies) ===")
    multi_result = benchmark_multiple(original_code, strategies, args)

    for r in multi_result["all_results"]:
        status = "✅ PASSED" if r["benchmark"]["passed"] else "❌ FAILED"
        print(f"  {status} — {r['name']}: {r['benchmark']}")

    if multi_result["best"]:
        best = multi_result["best"]
        print(f"\n✅ SUCCESS after 1 round. Best strategy: '{best['name']}' — Speedup: {best['benchmark']['speedup']}x")
        return {
            "success": True,
            "rounds": 1,
            "final_code": best["code"],
            "explanation": f"{best['name']}: {best['explanation']}",
            "benchmark": best["benchmark"],
            "all_strategies_tested": multi_result["all_results"],
        }

    # --- No strategy passed: fall back to single-strategy retry loop ---
    print("\n⚠️ None of the strategies passed. Falling back to single-strategy retry loop...\n")
    feedback = multi_result["all_results"][0]["benchmark"]

    for round_num in range(2, MAX_ROUNDS + 1):
        print(f"=== ROUND {round_num}: OPTIMIZER (single strategy, using feedback) ===")
        optimization = optimize_code(original_code, profiler_report, feedback)
        print(f"Explanation: {optimization['explanation']}\n")

        print(f"=== ROUND {round_num}: BENCHMARKER ===")
        result = benchmark(original_code, optimization["code"], args)
        print(json.dumps(result, indent=2))

        if result["passed"]:
            print(f"\n✅ SUCCESS after {round_num} round(s). Speedup: {result['speedup']}x")
            return {
                "success": True,
                "rounds": round_num,
                "final_code": optimization["code"],
                "explanation": optimization["explanation"],
                "benchmark": result,
            }

        print(f"\n❌ Round {round_num} failed, retrying with feedback...\n")
        feedback = result

    print(f"\n⚠️ Gave up after {MAX_ROUNDS} rounds without a passing optimization.")
    return {"success": False, "rounds": MAX_ROUNDS, "last_result": feedback}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <path_to_slow_code.py> [arg1 arg2 ...]")
        sys.exit(1)

    filepath = sys.argv[1]
    # args are passed as ints for the demo examples; adapt as needed
    cli_args = tuple(int(a) if a.isdigit() else a for a in sys.argv[2:])

    run_pipeline(filepath, cli_args)
"""
Orchestrator
Wires the three agents together into the feedback loop:

    Profiler -> Optimizer -> Benchmarker
                    ^              |
                    |___ feedback __|   (up to MAX_ROUNDS)

Run with: python orchestrator.py examples/slow_example_1.py
"""

import sys
import json

from agents.profiler import profile_code
from agents.optimizer import optimize_code
from agents.benchmarker import benchmark

MAX_ROUNDS = 3


def run_pipeline(filepath: str, args: tuple = ()):
    with open(filepath, "r") as f:
        original_code = f.read()

    print(f"\n=== PROFILER: analyzing {filepath} ===")
    profiler_report = profile_code(filepath, args)
    print(f"Baseline time: {profiler_report['baseline_time']}s")
    print(f"Top bottlenecks: {profiler_report['bottlenecks']}\n")

    feedback = None
    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"=== ROUND {round_num}: OPTIMIZER ===")
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
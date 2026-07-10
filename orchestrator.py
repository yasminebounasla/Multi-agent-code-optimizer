"""
Orchestrator
Wires the agents together into the multi-strategy pipeline:

    Profiler -> Optimizer (N strategies) -> Benchmarker (tests all)
                                                    |
                                    Explainer (complexity justification)
                                    Scorer (composite: speed + risk + readability)
                                                    |
                        best = highest composite_score among PASSED and NOT "reject"
                                                    |
                                    if none qualify -> single-strategy retry loop
                                                    (up to MAX_ROUNDS, using feedback)

Run with: python orchestrator.py examples/slow_example_1.py
"""

import sys
import os
import json

from agents.profiler import profile_code
from agents.optimizer import optimize_code, generate_strategies
from agents.benchmarker import benchmark, benchmark_multiple
from agents.explainer import explain_all, explain_optimization
from agents.scorer import score_all, score_candidate

MAX_ROUNDS = 3
NUM_STRATEGIES = 2  # temporarily reduced from 3 to stay under the daily token limit
OPTIMIZED_DIR = "optimized"


def _save_optimized_code(filepath: str, code: str) -> str:
    """Save the winning optimized code next to a mirror of the original filename,
    e.g. examples/slow_example_1.py -> optimized/slow_example_1_optimized.py"""
    os.makedirs(OPTIMIZED_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    out_path = os.path.join(OPTIMIZED_DIR, f"{base_name}_optimized.py")
    with open(out_path, "w") as f:
        f.write(code)
    return out_path


def _speedup_to_pseudo_times(speedup: float) -> tuple:
    """
    The scorer's speed component only needs the *ratio* between original
    and optimized time (time_original / time_optimized). The benchmarker
    already gives us that ratio directly as 'speedup', so we synthesize
    a pseudo (time_original, time_optimized) pair that preserves the
    exact ratio without depending on whatever raw timing keys
    benchmark() happens to return.
    """
    speedup = max(speedup, 1e-9)
    return 1.0, 1.0 / speedup


def _print_score_table(scored: list):
    print("\n  Composite scores (speed 50% / risk 30% / readability 20%):")
    print(f"  {'strategy':<32}{'speed':>7}{'risk':>7}{'read.':>7}{'composite':>11}  recommendation")
    for s in scored:
        print(
            f"  {s['name']:<32}{s['speed_score']:>7}{s['risk_score']:>7}"
            f"{s['readability_score']:>7}{s['composite_score']:>11}  {s['recommendation']}"
        )


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

    # Only Explainer/Scorer strategies that actually passed the benchmark --
    # no point spending LLM calls explaining/scoring code we already know is broken,
    # and it avoids crashing on a None speedup from a failed/crashed candidate.
    passed_results = [r for r in multi_result["all_results"] if r["benchmark"]["passed"]]

    if not passed_results:
        print("\n⚠️ All strategies failed the benchmark. Skipping Explainer/Scorer, falling back to retry loop...\n")
        feedback = multi_result["all_results"][0]["benchmark"]
        eligible_scored = []
        scored = []
        code_by_name = {s["name"]: s["code"] for s in strategies}
        explanation_by_name = {}
    else:
        passed_strategies = [s for s in strategies if s["name"] in {r["name"] for r in passed_results}]

        # --- Explainer: complexity justification for passing strategies only ---
        print("\n=== ROUND 1: EXPLAINER (complexity justification) ===")
        explanations = explain_all(original_code, passed_strategies)
        explanation_by_name = {e["name"]: e["explanation"] for e in explanations}
        for e in explanations:
            exp = e["explanation"]
            print(
                f"  - {e['name']}: {exp['original_complexity']} -> {exp['optimized_complexity']} "
                f"[{exp['verdict']}] — {exp['mechanism']}"
            )

        # --- Scorer: composite score (speed + risk + readability) for passing strategies only ---
        print("\n=== ROUND 1: SCORER (composite: speed + risk + readability) ===")
        code_by_name = {s["name"]: s["code"] for s in strategies}
        scoring_candidates = []
        for r in passed_results:
            time_original, time_optimized = _speedup_to_pseudo_times(r["benchmark"]["speedup"])
            scoring_candidates.append(
                {
                    "name": r["name"],
                    "code": code_by_name[r["name"]],
                    "time_original": time_original,
                    "time_optimized": time_optimized,
                }
            )
        scored = score_all(original_code, scoring_candidates)
        _print_score_table(scored)

        # Pick the best candidate: highest composite score among those that
        # were NOT flagged "reject" by the Scorer (high risk). All candidates
        # here already passed the benchmark, so no need to re-check that.
        eligible_scored = [s for s in scored if s["recommendation"] != "reject"]

    if eligible_scored:
        best_score = eligible_scored[0]  # scored list is already sorted best-first
        best_result = next(
            r for r in multi_result["all_results"] if r["name"] == best_score["name"]
        )
        best_strategy = next(s for s in strategies if s["name"] == best_score["name"])
        best_code = code_by_name[best_score["name"]]

        print(
            f"\n✅ SUCCESS after 1 round. Best strategy: '{best_score['name']}' "
            f"— Speedup: {best_result['benchmark']['speedup']}x "
            f"— Composite score: {best_score['composite_score']}/10"
        )
        saved_path = _save_optimized_code(filepath, best_code)
        print(f"Optimized code saved to: {saved_path}")
        return {
            "success": True,
            "rounds": 1,
            "final_code": best_code,
            "saved_path": saved_path,
            "explanation": f"{best_strategy['name']}: {best_strategy['explanation']}",
            "complexity_explanation": explanation_by_name.get(best_score["name"]),
            "score": best_score,
            "benchmark": best_result["benchmark"],
            "all_strategies_tested": multi_result["all_results"],
            "all_scores": scored,
        }

    # --- No eligible strategy: fall back to single-strategy retry loop ---
    if scored and not eligible_scored:
        print("\n⚠️ All strategies either failed the benchmark or were flagged high-risk by the Scorer.")
    print("Falling back to single-strategy retry loop...\n")
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

            print(f"\n=== ROUND {round_num}: EXPLAINER ===")
            complexity_explanation = explain_optimization(
                original_code, optimization["code"], strategy_name="retry"
            )
            print(
                f"  {complexity_explanation['original_complexity']} -> "
                f"{complexity_explanation['optimized_complexity']} "
                f"[{complexity_explanation['verdict']}] — {complexity_explanation['mechanism']}"
            )

            print(f"\n=== ROUND {round_num}: SCORER ===")
            time_original, time_optimized = _speedup_to_pseudo_times(result.get("speedup", 1.0))
            score = score_candidate(
                original_code,
                optimization["code"],
                time_original,
                time_optimized,
                strategy_name="retry",
            )
            print(
                f"  speed={score['speed_score']} risk={score['risk_score']} "
                f"readability={score['readability_score']} "
                f"composite={score['composite_score']} -> {score['recommendation']}"
            )

            if score["recommendation"] == "reject":
                print(f"\n⚠️ Round {round_num} passed the benchmark but was flagged high-risk. Retrying...\n")
                feedback = result
                continue

            saved_path = _save_optimized_code(filepath, optimization["code"])
            print(f"Optimized code saved to: {saved_path}")
            return {
                "success": True,
                "rounds": round_num,
                "final_code": optimization["code"],
                "saved_path": saved_path,
                "explanation": optimization["explanation"],
                "complexity_explanation": complexity_explanation,
                "score": score,
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
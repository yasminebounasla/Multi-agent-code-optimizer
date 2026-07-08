"""
Runs the full Profiler -> Optimizer -> Benchmarker pipeline on every example
in examples/, and prints a summary table at the end.

Run with: python run_all.py
"""

from orchestrator import run_pipeline

# Each example's run(n) takes a single int; sizes tuned so the ORIGINAL
# code takes a noticeable but reasonable amount of time (not instant, not minutes).
EXAMPLES = [
    ("examples/slow_example_1.py", (2000,), "Nested loop duplicate finder (O(n^2))"),
    ("examples/slow_example_2.py", (28,), "Naive recursive Fibonacci (no memoization)"),
    ("examples/slow_example_3.py", (300000,), "String += in a loop instead of join()"),
    ("examples/slow_example_4.py", (3000,), "List membership check instead of set"),
    ("examples/slow_example_5.py", (5000,), "Redundant sort recomputed every iteration"),
]


def main():
    summary = []

    for filepath, args, description in EXAMPLES:
        print(f"\n{'#' * 70}")
        print(f"# {description}")
        print(f"{'#' * 70}")

        result = run_pipeline(filepath, args)

        if result["success"]:
            bm = result["benchmark"]
            summary.append({
                "example": description,
                "rounds": result["rounds"],
                "speedup": bm["speedup"],
                "original_time": bm["original_time"],
                "optimized_time": bm["optimized_time"],
            })
        else:
            summary.append({
                "example": description,
                "rounds": result["rounds"],
                "speedup": None,
                "original_time": None,
                "optimized_time": None,
            })

    print(f"\n\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    for row in summary:
        if row["speedup"] is not None:
            print(f"{row['example']:<50} {row['speedup']:>8}x  ({row['rounds']} round(s))")
        else:
            print(f"{row['example']:<50} {'FAILED':>8}  ({row['rounds']} round(s))")


if __name__ == "__main__":
    main()
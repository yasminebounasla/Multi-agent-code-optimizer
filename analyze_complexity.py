"""
Runs empirical Big-O analysis on an example's original code vs its optimized
version (must already exist in optimized/, created by orchestrator.py), and
saves a before/after time-vs-size chart.

Usage:
    python analyze_complexity.py examples/slow_example_1.py --sizes 500 1000 2000 4000
"""

import sys
import os
import argparse
import matplotlib
matplotlib.use("Agg")  # no GUI backend needed, just save to file
import matplotlib.pyplot as plt

from agents.complexity import estimate_complexity_from_code

CHARTS_DIR = "complexity_charts"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("original_file", help="path to the original slow example, e.g. examples/slow_example_1.py")
    parser.add_argument("--sizes", nargs="+", type=int, default=[500, 1000, 2000, 4000, 8000],
                         help="input sizes to test (space-separated)")
    args = parser.parse_args()

    base_name = os.path.splitext(os.path.basename(args.original_file))[0]
    optimized_path = os.path.join("optimized", f"{base_name}_optimized.py")

    if not os.path.exists(optimized_path):
        print(f"❌ No optimized version found at {optimized_path}.")
        print("   Run 'python orchestrator.py <file> <arg>' first to generate it.")
        sys.exit(1)

    with open(args.original_file) as f:
        original_code = f.read()
    with open(optimized_path) as f:
        optimized_code = f.read()

    print(f"Analyzing complexity for: {base_name}")
    print(f"Sizes tested: {args.sizes}\n")

    print("Running ORIGINAL across sizes...")
    original_result = estimate_complexity_from_code(original_code, args.sizes)
    print(f"  -> {original_result['complexity']} (slope={original_result['slope']})")

    print("Running OPTIMIZED across sizes...")
    optimized_result = estimate_complexity_from_code(optimized_code, args.sizes)
    print(f"  -> {optimized_result['complexity']} (slope={optimized_result['slope']})")

    # --- Plot ---
    os.makedirs(CHARTS_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(original_result["sizes"], original_result["times"], marker="o",
            label=f"Original — {original_result['complexity']}", color="#e74c3c")
    ax.plot(optimized_result["sizes"], optimized_result["times"], marker="o",
            label=f"Optimized — {optimized_result['complexity']}", color="#2ecc71")

    ax.set_xlabel("Input size (n)")
    ax.set_ylabel("Execution time (s)")
    ax.set_title(f"Complexity comparison: {base_name}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, which="both", linestyle="--", alpha=0.4)

    out_path = os.path.join(CHARTS_DIR, f"{base_name}_complexity.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n✅ Chart saved to: {out_path}")


if __name__ == "__main__":
    main()
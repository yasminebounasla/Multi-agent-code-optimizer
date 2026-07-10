"""
Builds report.html WITHOUT calling the LLM at all.

Uses:
  1. The REAL metrics already obtained from previous successful runs
     (speedup, complexity verdict, scores) -- transcribed below.
  2. The REAL optimized code already saved on disk in optimized/
     (from your earlier successful `python run_all.py` / `generate_report.py` runs).

This exists purely to survive the Groq daily rate limit -- it re-uses
real results you already produced, it does not fabricate new ones.

Usage:
    python build_report_offline.py
"""

import os
from generate_report import CSS, _render_example, REPORT_PATH
import html as html_lib
from datetime import datetime

# --- Real results, transcribed from your last successful terminal runs ---
RESULTS = {
    "examples/slow_example_1.py": {
        "description": "Nested loop duplicate finder (O(n^2))",
        "success": True, "rounds": 1,
        "explanation": "Set-based lookup: uses a set for O(1) lookup instead of a list",
        "complexity_explanation": {
            "original_complexity": "O(n^2)", "optimized_complexity": "O(n)",
            "verdict": "genuine_improvement",
            "mechanism": "Replacing a nested loop with set-based lookup, reducing the time complexity from quadratic to linear",
        },
        "score": {"name": "Set-based lookup", "composite_score": 10.0},
        "benchmark": {"speedup": 266.39, "passed": True},
        "all_strategies_tested": [
            {"name": "Set-based lookup", "benchmark": {"passed": True, "speedup": 266.39, "error": None}},
            {"name": "List comprehension with collections.Counter", "benchmark": {"passed": True, "speedup": 318.33, "error": None}},
            {"name": "NumPy-based vectorized solution", "benchmark": {"passed": True, "speedup": 223.78, "error": None}},
        ],
        "all_scores": [
            {"name": "Set-based lookup", "speed_score": 10.0, "risk_score": 0.0, "readability_score": 10.0, "composite_score": 10.0, "recommendation": "adopt"},
            {"name": "List comprehension with collections.Counter", "speed_score": 10.0, "risk_score": 0.0, "readability_score": 10.0, "composite_score": 10.0, "recommendation": "adopt"},
            {"name": "NumPy-based vectorized solution", "speed_score": 10.0, "risk_score": 2.0, "readability_score": 8.0, "composite_score": 9.0, "recommendation": "adopt"},
        ],
    },
    "examples/slow_example_2.py": {
        "description": "Naive recursive Fibonacci (no memoization)",
        "success": True, "rounds": 1,
        "explanation": "Iterative approach: avoids recursive call overhead using a loop",
        "complexity_explanation": {
            "original_complexity": "O(2^n)", "optimized_complexity": "O(n)",
            "verdict": "genuine_improvement",
            "mechanism": "Replaces the naive recursive approach with an iterative solution, eliminating the massive redundant recomputation by storing and reusing previously computed values.",
        },
        "score": {"name": "Iterative approach", "composite_score": 10.0},
        "benchmark": {"speedup": 60328.6, "passed": True},
        "all_strategies_tested": [
            {"name": "Memoization with dict", "benchmark": {"passed": True, "speedup": 10164.04, "error": None}},
            {"name": "Iterative approach", "benchmark": {"passed": True, "speedup": 60328.6, "error": None}},
            {"name": "Matrix exponentiation", "benchmark": {"passed": True, "speedup": 5828.79, "error": None}},
        ],
        "all_scores": [
            {"name": "Iterative approach", "speed_score": 10.0, "risk_score": 0.0, "readability_score": 10.0, "composite_score": 10.0, "recommendation": "adopt"},
            {"name": "Memoization with dict", "speed_score": 10.0, "risk_score": 0.0, "readability_score": 9.0, "composite_score": 9.8, "recommendation": "adopt"},
            {"name": "Matrix exponentiation", "speed_score": 10.0, "risk_score": 2.0, "readability_score": 8.0, "composite_score": 9.0, "recommendation": "adopt"},
        ],
    },
    "examples/slow_example_3.py": {
        "description": "String += in a loop instead of join()",
        "success": True, "rounds": 1,
        "explanation": "List and Join: builds a list and joins once instead of repeated concatenation",
        "complexity_explanation": {
            "original_complexity": "O(n^2)", "optimized_complexity": "O(n)",
            "verdict": "genuine_improvement",
            "mechanism": "Replacing string concatenation with list append and join, avoiding the overhead of creating a new string and copying the entire string in each iteration",
        },
        "score": {"name": "List and Join", "composite_score": 6.24},
        "benchmark": {"speedup": 2.63, "passed": True},
        "all_strategies_tested": [
            {"name": "List and Join", "benchmark": {"passed": True, "speedup": 2.63, "error": None}},
            {"name": "Generator Expression with Join", "benchmark": {"passed": False, "speedup": 3.16, "error": "Output mismatch: optimized result differs from original"}},
            {"name": "String Formatting with List Comprehension", "benchmark": {"passed": False, "speedup": 5.32, "error": "Output mismatch: optimized result differs from original"}},
        ],
        "all_scores": [
            {"name": "List and Join", "speed_score": 2.47, "risk_score": 0.0, "readability_score": 10.0, "composite_score": 6.24, "recommendation": "review"},
        ],
    },
    "examples/slow_example_4.py": {
        "description": "List membership check instead of set",
        "success": True, "rounds": 1,
        "explanation": "List Comprehension with Set Intersection: uses set intersection to find common elements",
        "complexity_explanation": {
            "original_complexity": "O(n*m)", "optimized_complexity": "O(n + m)",
            "verdict": "genuine_improvement",
            "mechanism": "Converting lists to sets allows for O(1) average lookup time, replacing the O(n) membership check in the original code with a set intersection operation",
        },
        "score": {"name": "List Comprehension with Set Intersection", "composite_score": 10.0},
        "benchmark": {"speedup": 227.93, "passed": True},
        "all_strategies_tested": [
            {"name": "Set Lookup Optimization", "benchmark": {"passed": True, "speedup": 195.17, "error": None}},
            {"name": "List Comprehension with Set Intersection", "benchmark": {"passed": True, "speedup": 227.93, "error": None}},
            {"name": "Numpy Array Intersection", "benchmark": {"passed": True, "speedup": 239.39, "error": None}},
        ],
        "all_scores": [
            {"name": "List Comprehension with Set Intersection", "speed_score": 10.0, "risk_score": 0.0, "readability_score": 10.0, "composite_score": 10.0, "recommendation": "adopt"},
            {"name": "Set Lookup Optimization", "speed_score": 10.0, "risk_score": 0.0, "readability_score": 9.0, "composite_score": 9.8, "recommendation": "adopt"},
            {"name": "Numpy Array Intersection", "speed_score": 10.0, "risk_score": 2.0, "readability_score": 9.0, "composite_score": 9.2, "recommendation": "adopt"},
        ],
    },
    "examples/slow_example_5.py": {
        "description": "Redundant sort recomputed every iteration",
        "success": True, "rounds": 1,
        "explanation": "Using a dictionary for indexing: precomputes index lookup instead of repeated sort+index",
        "complexity_explanation": {
            "original_complexity": "O(n*m*log(n))", "optimized_complexity": "O(n*log(n) + m)",
            "verdict": "genuine_improvement",
            "mechanism": "The original code had a redundant sorting operation inside a loop, which has been removed in the optimized code. Additionally, a dictionary is used for faster indexing, reducing the time complexity from O(n) to O(1) for the index lookup.",
        },
        "score": {"name": "Using a dictionary for indexing", "composite_score": 9.8},
        "benchmark": {"speedup": 88.97, "passed": True},
        "all_strategies_tested": [
            {"name": "Hoisting Invariant Computation", "benchmark": {"passed": True, "speedup": 2.14, "error": None}},
            {"name": "Using a set for membership testing", "benchmark": {"passed": True, "speedup": 2.95, "error": None}},
            {"name": "Using a dictionary for indexing", "benchmark": {"passed": True, "speedup": 88.97, "error": None}},
        ],
        "all_scores": [
            {"name": "Using a dictionary for indexing", "speed_score": 10.0, "risk_score": 0.0, "readability_score": 9.0, "composite_score": 9.8, "recommendation": "adopt"},
            {"name": "Using a set for membership testing", "speed_score": 2.77, "risk_score": 0.0, "readability_score": 9.0, "composite_score": 6.18, "recommendation": "review"},
            {"name": "Hoisting Invariant Computation", "speed_score": 1.94, "risk_score": 0.0, "readability_score": 10.0, "composite_score": 5.97, "recommendation": "review"},
        ],
    },
}


def build():
    sections = []
    summary_rows = ""

    for filepath, result in RESULTS.items():
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        optimized_path = os.path.join("optimized", f"{base_name}_optimized.py")

        if not os.path.exists(filepath):
            print(f"⚠️  Missing {filepath}, skipping.")
            continue
        if not os.path.exists(optimized_path):
            print(f"⚠️  Missing {optimized_path} -- run orchestrator.py on this example at least once first.")
            continue

        with open(filepath) as f:
            original_code = f.read()
        with open(optimized_path) as f:
            result["final_code"] = f.read()

        description = result["description"]
        sections.append(_render_example(description, filepath, original_code, result))

        summary_rows += f"""
          <tr>
            <td>{html_lib.escape(description)}</td>
            <td><span class="speedup" style="font-size:14px">{result['benchmark']['speedup']}x</span></td>
            <td>{result['rounds']}</td>
            <td>{result['score']['composite_score']}</td>
          </tr>
        """

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Agentic Performance Optimizer — Report</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
  <h1>Agentic Performance Optimizer</h1>
  <div class="subtitle">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} — Profiler → Optimizer → Benchmarker → Explainer → Scorer</div>

  <div class="section-label">Summary</div>
  <table class="summary-table">
    <tr><th>Example</th><th>Best speedup</th><th>Rounds</th><th>Composite score</th></tr>
    {summary_rows}
  </table>

  {''.join(sections)}
</div>
</body>
</html>
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(html_doc)

    print(f"\n✅ Report generated (no API calls used): {REPORT_PATH}")


if __name__ == "__main__":
    build()
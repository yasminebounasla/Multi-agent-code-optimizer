"""
Empirical Big-O complexity estimation.

Idea: run the code on several increasing input sizes, measure real execution
time for each, then fit a line to log(time) vs log(size). The SLOPE of that
line approximates the polynomial degree of the time complexity:

    slope ≈ 0   -> O(1)        constant
    slope ≈ 1   -> O(n)        linear
    slope ≈ 2   -> O(n^2)      quadratic
    slope ≈ 3   -> O(n^3)      cubic
    (O(log n) and O(n log n) don't fit this model perfectly, but they show up
     as slopes noticeably below 1, or between 1 and 2 respectively)

This is an empirical estimate, not a mathematical proof -- it's the same
technique used informally by developers who plot "time vs input size" to
sanity-check an algorithm's growth rate.
"""

import time
import importlib.util
import tempfile
import os
import math


def _load_module_from_source(code: str):
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    tmp.write(code)
    tmp.close()
    spec = importlib.util.spec_from_file_location("complexity_module", tmp.name)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        os.unlink(tmp.name)
    return module


def _time_run(module, n, repeats=3):
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        module.run(n)
        elapsed = time.perf_counter() - start
        best = min(best, elapsed)
    return best


def _estimate_slope(sizes, times):
    """Linear regression on log(size) vs log(time) -> returns the slope."""
    log_sizes = [math.log(s) for s in sizes]
    log_times = [math.log(t) if t > 0 else math.log(1e-9) for t in times]

    n = len(sizes)
    mean_x = sum(log_sizes) / n
    mean_y = sum(log_times) / n

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(log_sizes, log_times))
    denominator = sum((x - mean_x) ** 2 for x in log_sizes)

    return numerator / denominator if denominator != 0 else 0.0


def _classify_slope(slope: float) -> str:
    if slope < 0.3:
        return "O(1) constant"
    elif slope < 0.8:
        return "O(log n) logarithmic"
    elif slope < 1.3:
        return "O(n) linear"
    elif slope < 1.8:
        return "O(n log n) linearithmic"
    elif slope < 2.5:
        return "O(n^2) quadratic"
    elif slope < 3.5:
        return "O(n^3) cubic"
    else:
        return f"O(n^{slope:.1f}) (high polynomial or worse)"


def estimate_complexity_from_code(code: str, sizes: list) -> dict:
    """
    Run `code`'s run(n) function across the given sizes, measure real time
    for each, and estimate the empirical Big-O complexity.

    Returns: {"sizes": [...], "times": [...], "slope": float, "complexity": str}
    """
    module = _load_module_from_source(code)

    times = []
    for n in sizes:
        elapsed = _time_run(module, n)
        times.append(elapsed)

    slope = _estimate_slope(sizes, times)
    complexity = _classify_slope(slope)

    return {"sizes": sizes, "times": times, "slope": round(slope, 2), "complexity": complexity}
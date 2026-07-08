"""
Benchmarker Agent
Role: the objective judge. Actually executes the original and the
optimized code on the same inputs, checks the outputs are equal, and
measures real execution time with timeit. No opinions, just numbers.

Output: {
    "passed": bool,               # True only if output matches AND it's faster
    "outputs_match": bool,
    "original_time": float,
    "optimized_time": float,
    "speedup": float,              # original_time / optimized_time
    "error": str | None            # populated if the optimized code crashed
}
"""

import timeit
import importlib.util
import tempfile
import os


def _safe_equals(a, b) -> bool:
    """
    Compare two results for equality, safely handling cases where `==`
    doesn't return a plain bool (e.g. numpy arrays, where a == b returns
    an element-wise array instead of a single True/False).
    """
    try:
        eq = a == b
        if hasattr(eq, "all"):  # numpy array or similar
            return bool(eq.all())
        return bool(eq)
    except Exception:
        return False


def _load_module_from_source(code: str):
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    tmp.write(code)
    tmp.close()
    spec = importlib.util.spec_from_file_location("candidate_module", tmp.name)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        os.unlink(tmp.name)
    return module


def benchmark(original_code: str, optimized_code: str, args: tuple, number: int = 5) -> dict:
    original_module = _load_module_from_source(original_code)
    original_result = original_module.run(*args)
    original_time = timeit.timeit(lambda: original_module.run(*args), number=number) / number

    try:
        optimized_module = _load_module_from_source(optimized_code)
        optimized_result = optimized_module.run(*args)
    except Exception as e:
        return {
            "passed": False,
            "outputs_match": False,
            "original_time": round(original_time, 6),
            "optimized_time": None,
            "speedup": None,
            "error": f"Optimized code crashed: {e}",
        }

    outputs_match = _safe_equals(optimized_result, original_result)

    optimized_time = timeit.timeit(lambda: optimized_module.run(*args), number=number) / number
    speedup = (original_time / optimized_time) if optimized_time > 0 else float("inf")

    passed = outputs_match and optimized_time < original_time

    return {
        "passed": passed,
        "outputs_match": outputs_match,
        "original_time": round(original_time, 6),
        "optimized_time": round(optimized_time, 6),
        "speedup": round(speedup, 2),
        "error": None if outputs_match else "Output mismatch: optimized result differs from original",
    }


def benchmark_multiple(original_code: str, candidates: list, args: tuple, number: int = 5) -> dict:
    """
    Benchmark several candidate optimizations (each a {name, explanation, code} dict)
    against the same original code, and return the best one that passed.

    Returns: {
        "best": {name, explanation, code, benchmark} | None,   # None if nothing passed
        "all_results": [{name, benchmark}, ...]                 # every candidate tested
    }
    """
    all_results = []
    passing_candidates = []

    for candidate in candidates:
        result = benchmark(original_code, candidate["code"], args, number=number)
        all_results.append({"name": candidate["name"], "benchmark": result})

        if result["passed"]:
            passing_candidates.append({**candidate, "benchmark": result})

    if not passing_candidates:
        return {"best": None, "all_results": all_results}

    # Keep the candidate with the highest measured speedup among those that passed
    best = max(passing_candidates, key=lambda c: c["benchmark"]["speedup"])
    return {"best": best, "all_results": all_results}
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

    outputs_match = (optimized_result == original_result)

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
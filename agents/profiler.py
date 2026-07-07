"""
Profiler Agent
Role: run the given code with cProfile on a real input and produce a
structured report of where the time is actually going.

Input: path to a python file exposing a `run(*args)` function, plus the
       arguments to call it with.
Output: {
    "baseline_time": float,          # total wall time in seconds
    "bottlenecks": [
        {"function": str, "cumulative_time": float, "calls": int}
    ],
    "raw_stats": str                  # human-readable pstats dump (for the LLM to read)
}
"""

import cProfile
import pstats
import io
import importlib.util
import time


def _load_module(filepath: str):
    spec = importlib.util.spec_from_file_location("target_module", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile_code(filepath: str, args: tuple) -> dict:
    module = _load_module(filepath)

    profiler = cProfile.Profile()

    start = time.perf_counter()
    profiler.enable()
    result = module.run(*args)
    profiler.disable()
    elapsed = time.perf_counter() - start

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(10)  # top 10 functions by cumulative time

    bottlenecks = []
    for func, stat in list(stats.stats.items())[:10]:
        filename, lineno, funcname = func
        cc, nc, tt, ct, callers = stat
        bottlenecks.append({
            "function": funcname,
            "cumulative_time": round(ct, 6),
            "calls": nc,
        })

    return {
        "baseline_time": round(elapsed, 6),
        "bottlenecks": bottlenecks,
        "raw_stats": stream.getvalue(),
        "result": result,  # kept so the Benchmarker can compare against it later
    }
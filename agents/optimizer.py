"""
Optimizer Agent
Role: given the original source code and the Profiler's report (and,
on later rounds, the Benchmarker's failure feedback), produce a rewritten
version of the code that should run faster while behaving identically.

Input: original source code (str), profiler report (dict), optional
       previous feedback (dict) from a failed round.
Output: {
    "explanation": str,     # short note on what was changed and why
    "code": str             # full new file content, must still define run(*args)
}
"""

from llm_client import ask_llm_json

SYSTEM_PROMPT = """You are a Python performance optimization expert.
You will be given the source code of a module that exposes a function `run(*args)`,
along with a profiling report showing where execution time is spent.

Your job: rewrite the module to be faster WITHOUT changing its observable behavior.
The function must still be named `run` and accept the same arguments, and must
return a value that is equal to the original output for the same inputs.

Rules:
- Do not remove or rename `run`.
- Do not change what `run` returns for the same inputs.
- Prefer standard library optimizations (better algorithms, data structures,
  caching, avoiding redundant work) over adding new dependencies.
- Keep the code readable.

Respond ONLY with a JSON object, no markdown, no preamble:
{
  "explanation": "short explanation of what you changed and why it's faster",
  "code": "full contents of the new python file as a single string"
}
"""


def optimize_code(original_code: str, profiler_report: dict, feedback: dict = None) -> dict:
    user_prompt = f"""ORIGINAL CODE:
```
{original_code}
```

PROFILER REPORT:
{profiler_report['raw_stats']}

Top bottlenecks: {profiler_report['bottlenecks']}
Baseline time: {profiler_report['baseline_time']}s
"""

    if feedback:
        user_prompt += f"""

PREVIOUS ATTEMPT FAILED. Benchmarker feedback:
{feedback}

Fix the issue above in this new attempt.
"""

    return ask_llm_json(SYSTEM_PROMPT, user_prompt)
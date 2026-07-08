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


MULTI_STRATEGY_SYSTEM_PROMPT = """You are a Python performance optimization expert.
You will be given the source code of a module that exposes a function `run(*args)`,
along with a profiling report showing where execution time is spent.

Your job: propose MULTIPLE distinct optimization strategies (not variations of the
same idea) that make the code faster WITHOUT changing its observable behavior.
Each strategy must still define a function named `run` with the same signature,
and must return a value equal to the original output for the same inputs.

Rules:
- Do not remove or rename `run`.
- Do not change what `run` returns for the same inputs.
- Each strategy should use a genuinely different approach (e.g. different data
  structure, caching vs algorithmic rewrite, vectorization vs iterative fix) --
  not the same fix with cosmetic changes.
- Prefer standard library optimizations over adding new dependencies.
- Keep the code readable.

Respond ONLY with a JSON object, no markdown, no preamble:
{
  "strategies": [
    {
      "name": "short strategy name, e.g. 'Memoization with dict'",
      "explanation": "why this approach should be faster",
      "code": "full contents of the new python file as a single string"
    }
  ]
}
"""


def generate_strategies(original_code: str, profiler_report: dict, num_strategies: int = 3) -> list:
    """
    Ask the LLM for `num_strategies` genuinely different optimization approaches
    in a single call. Returns a list of {name, explanation, code} dicts.
    """
    user_prompt = f"""ORIGINAL CODE:
```
{original_code}
```

PROFILER REPORT:
{profiler_report['raw_stats']}

Top bottlenecks: {profiler_report['bottlenecks']}
Baseline time: {profiler_report['baseline_time']}s

Propose exactly {num_strategies} genuinely different optimization strategies.
"""

    response = ask_llm_json(MULTI_STRATEGY_SYSTEM_PROMPT, user_prompt)
    return response["strategies"]
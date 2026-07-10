# Agentic Performance Optimizer

A multi-agent system that takes slow Python code and makes it faster — automatically, with proof. Built for the AI Club "Multi-Agent Collaboration System" challenge.

## Why this task

Instead of a single LLM call optimizing code and being trusted blindly, this system splits the work across specialized agents so that every decision — "is this actually correct?", "is it actually faster?", "is it actually safe?" — is backed by real execution and measurement, not LLM opinion.

## Agents

| Agent | Role | Uses LLM? |
|---|---|---|
| **Profiler** | Runs the code with `cProfile` on a real input, reports actual bottlenecks | No — real execution only |
| **Optimizer** | Proposes 2-3 genuinely different optimization strategies targeting those bottlenecks | Yes (Groq API) |
| **Benchmarker** | Executes original vs each candidate on the same input, checks outputs are identical, measures real speedup with `timeit` | No — real execution only |
| **Explainer** | Independently justifies *why* the winning strategy is faster, in terms of algorithmic complexity (Big-O) | Yes (Groq API) |
| **Scorer** | Composite score (speed 50% / risk 30% / readability 20%); rejects high-risk candidates even if fast | Speed: deterministic. Risk/readability: LLM |

**Design choice**: only the Optimizer, Explainer, and Scorer call an LLM. The Profiler and Benchmarker deliberately rely on real code execution rather than LLM reasoning, since measuring performance and comparing outputs are objective tasks better solved by execution than by inference. This keeps the whole pipeline grounded in real numbers rather than LLM opinion.

## How agents communicate

All handoffs are structured dicts/JSON, not raw text:
- Profiler → Optimizer: `{baseline_time, bottlenecks, raw_stats}`
- Optimizer → Benchmarker: `[{name, explanation, code}, ...]` (one per strategy)
- Benchmarker → Scorer: `{passed, outputs_match, speedup, error}` per candidate
- Scorer → Orchestrator: `{speed_score, risk_score, readability_score, composite_score, recommendation}`

## The pipeline

```
Profiler (measure bottlenecks)
        |
Optimizer (propose 3 strategies)
        |
Benchmarker (test all 3: correctness + speed)
        |
Explainer (complexity justification, passing strategies only)
        |
Scorer (composite score: speed + risk + readability)
        |
Best = highest composite score, among PASSED and NOT "reject"
        |
   if none qualify -> single-strategy retry loop (up to 3 rounds, using feedback)
```

## Example results

| Example | Bottleneck type | Best speedup |
|---|---|---|
| Nested loop duplicate finder | O(n²) nested loop | ~220-350x |
| Naive recursive Fibonacci | Exponential redundant recomputation | ~7,000-77,000x |
| String `+=` in a loop | O(n²) string immutability | ~2-4x |
| List membership check | O(n·m) list lookup | ~170-430x |
| Redundant sort in a loop | Invariant recomputed every iteration | ~2-4x |

The variation is intentional and honest — not every bottleneck has room for a 100x+ fix. Some are fundamental complexity-class fixes (huge gains), others are constant-factor improvements (modest, still real gains).

## How to run

```bash
pip install -r requirements.txt
export GROQ_API_KEY="your_key_here"   # or $env:GROQ_API_KEY="..." on PowerShell

# Run on a single example
python orchestrator.py examples/slow_example_1.py 2000

# Run on all 5 examples with a summary table
python run_all.py

# Generate the full HTML report (re-runs everything, writes report.html)
python generate_report.py

# Empirically estimate Big-O complexity + generate a before/after chart
# (requires an optimized/ file already produced by orchestrator.py)
python analyze_complexity.py examples/slow_example_1.py --sizes 500 1000 2000 4000 8000
```

## Project structure

```
agents/
  profiler.py      # cProfile-based profiling (no LLM)
  optimizer.py     # LLM proposes 1 or 3 optimization strategies
  benchmarker.py   # runs candidates, compares correctness + speed (no LLM)
  explainer.py     # LLM justifies speedup via algorithmic complexity
  scorer.py        # composite score: speed (deterministic) + risk/readability (LLM)
  complexity.py    # empirical Big-O estimation via log-log regression (no LLM)
orchestrator.py    # wires the full pipeline + retry loop
run_all.py         # runs all 5 examples, prints summary table
generate_report.py # runs all 5 examples, writes a self-contained HTML report
analyze_complexity.py  # Big-O comparison chart for one example
llm_client.py      # Groq API wrapper, with JSON-repair fallback (LLMs sometimes
                    # mix Python triple-quotes into JSON, or emit unescaped newlines)
examples/           # 5 example scripts, each with a different bottleneck type
optimized/          # winning optimized code saved here after a successful run
complexity_charts/  # generated Big-O comparison charts (PNG)
```

## Challenges encountered

- **JSON parsing fragility**: the LLM sometimes wraps code in Python-style triple quotes (`"""..."""`) instead of valid JSON escaping, or emits raw newlines inside JSON strings. Fixed with a repair step in `llm_client.py` (regex-based triple-quote conversion, `strict=False` parsing).
- **Type comparison across strategies**: a NumPy-based candidate returned an array, and `==` on arrays doesn't produce a plain bool — crashed the Benchmarker. Fixed with a `_safe_equals()` helper that handles array-like results.
- **Composite score ceiling effect**: the Scorer's speed score caps at 10/10 above ~50x speedup, so a 230x and a 470x candidate can tie on composite score even though one is meaningfully faster. This is a deliberate tradeoff (so raw speed doesn't dominate readability/risk beyond a "fast enough" threshold), but worth knowing when reading the scores.
- **Empirical complexity noise on very fast code**: on code that runs in microseconds, measurement noise can distort the estimated Big-O slope. Larger input sizes are needed to get a clean signal (see `analyze_complexity.py`).

## What we'd improve with more time

- Extend to other languages (currently Python-only; profiling/execution layer would need to be swapped per language)
- Migrate the hand-built pipeline to a framework (LangGraph/CrewAI) and compare
- Let the Scorer's weights (speed/risk/readability) be tuned per use case instead of fixed defaults
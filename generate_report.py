"""
Generates a single self-contained HTML report summarizing the full run:
for every example, shows the strategies tried, benchmark results, the
Explainer's complexity verdict, the Scorer's composite table, and a
before/after code diff for the winning strategy.

Usage:
    python generate_report.py
    (runs the same EXAMPLES list as run_all.py, then writes report.html)
"""

import os
import html
import difflib
from datetime import datetime

from orchestrator import run_pipeline

EXAMPLES = [
    ("examples/slow_example_1.py", (2000,), "Nested loop duplicate finder (O(n^2))"),
    ("examples/slow_example_2.py", (28,), "Naive recursive Fibonacci (no memoization)"),
    ("examples/slow_example_3.py", (300000,), "String += in a loop instead of join()"),
    ("examples/slow_example_4.py", (3000,), "List membership check instead of set"),
    ("examples/slow_example_5.py", (5000,), "Redundant sort recomputed every iteration"),
]

REPORT_PATH = "report.html"

CSS = """
:root {
  --bg: #0f1115;
  --panel: #161922;
  --border: #262b36;
  --text: #e6e8ec;
  --muted: #9aa3b2;
  --green: #3ddc84;
  --red: #ff6b6b;
  --accent: #5b8cff;
}
* { box-sizing: border-box; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, Segoe UI, Roboto, sans-serif;
  margin: 0;
  padding: 40px 24px 80px;
  line-height: 1.5;
}
.container { max-width: 980px; margin: 0 auto; }
h1 { font-size: 28px; margin-bottom: 4px; }
.subtitle { color: var(--muted); margin-bottom: 32px; font-size: 14px; }
.summary-table, .strategy-table, .score-table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0 32px;
  font-size: 14px;
}
.summary-table th, .strategy-table th, .score-table th {
  text-align: left;
  color: var(--muted);
  font-weight: 600;
  border-bottom: 1px solid var(--border);
  padding: 8px 10px;
}
.summary-table td, .strategy-table td, .score-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
}
.summary-table tr:hover, .strategy-table tr:hover, .score-table tr:hover { background: #1b1f29; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.badge.pass { background: rgba(61,220,132,0.15); color: var(--green); }
.badge.fail { background: rgba(255,107,107,0.15); color: var(--red); }
.badge.adopt { background: rgba(61,220,132,0.15); color: var(--green); }
.badge.reject { background: rgba(255,107,107,0.15); color: var(--red); }
.badge.review { background: rgba(255,196,0,0.15); color: #ffc400; }
.example {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 24px;
  margin-bottom: 28px;
}
.example h2 { margin-top: 0; font-size: 19px; }
.winner-box {
  background: rgba(61,220,132,0.08);
  border: 1px solid rgba(61,220,132,0.3);
  border-radius: 8px;
  padding: 14px 18px;
  margin: 16px 0;
}
.winner-box .speedup { color: var(--green); font-weight: 700; font-size: 20px; }
.mechanism { color: var(--muted); font-size: 13px; margin-top: 6px; }
pre {
  background: #0b0d12;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  overflow-x: auto;
  font-size: 12.5px;
  font-family: "SF Mono", Consolas, monospace;
}
.diff-add { color: var(--green); }
.diff-del { color: var(--red); }
.diff-ctx { color: var(--muted); }
.section-label {
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 11px;
  color: var(--muted);
  margin: 20px 0 8px;
  font-weight: 700;
}
"""


def _diff_html(original: str, optimized: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(), optimized.splitlines(),
        fromfile="original", tofile="optimized", lineterm=""
    )
    lines = []
    for line in diff:
        escaped = html.escape(line)
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(f'<span class="diff-add">{escaped}</span>')
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(f'<span class="diff-del">{escaped}</span>')
        else:
            lines.append(f'<span class="diff-ctx">{escaped}</span>')
    return "\n".join(lines) if lines else "(no textual diff available)"


def _render_example(description: str, filepath: str, original_code: str, result: dict) -> str:
    if not result["success"]:
        return f"""
        <div class="example">
          <h2>{html.escape(description)}</h2>
          <p style="color: var(--red)">⚠️ No optimization passed after {result['rounds']} round(s).</p>
        </div>
        """

    strategies_rows = ""
    for r in result.get("all_strategies_tested", []):
        bm = r["benchmark"]
        status = "pass" if bm["passed"] else "fail"
        speedup = f"{bm['speedup']}x" if bm.get("speedup") is not None else "—"
        strategies_rows += f"""
          <tr>
            <td>{html.escape(r['name'])}</td>
            <td><span class="badge {status}">{status.upper()}</span></td>
            <td>{speedup}</td>
            <td>{html.escape(bm.get('error') or '—')}</td>
          </tr>
        """

    score_rows = ""
    for s in result.get("all_scores", []):
        score_rows += f"""
          <tr>
            <td>{html.escape(s['name'])}</td>
            <td>{s['speed_score']}</td>
            <td>{s['risk_score']}</td>
            <td>{s['readability_score']}</td>
            <td><strong>{s['composite_score']}</strong></td>
            <td><span class="badge {s['recommendation']}">{s['recommendation']}</span></td>
          </tr>
        """

    complexity = result.get("complexity_explanation")
    complexity_html = ""
    if complexity:
        complexity_html = f"""
        <div class="mechanism">
          <strong>{html.escape(complexity['original_complexity'])} → {html.escape(complexity['optimized_complexity'])}</strong>
          [{html.escape(complexity['verdict'])}] — {html.escape(complexity['mechanism'])}
        </div>
        """

    diff_html = _diff_html(original_code, result["final_code"])

    return f"""
    <div class="example">
      <h2>{html.escape(description)}</h2>
      <div class="winner-box">
        Best strategy: <strong>{html.escape(result['explanation'].split(':')[0])}</strong>
        &nbsp;—&nbsp; <span class="speedup">{result['benchmark']['speedup']}x faster</span>
        &nbsp;—&nbsp; solved in {result['rounds']} round(s)
        {complexity_html}
      </div>

      {"<div class='section-label'>Strategies tested</div><table class='strategy-table'><tr><th>Strategy</th><th>Result</th><th>Speedup</th><th>Note</th></tr>" + strategies_rows + "</table>" if strategies_rows else ""}

      {"<div class='section-label'>Composite scores (speed 50% / risk 30% / readability 20%)</div><table class='score-table'><tr><th>Strategy</th><th>Speed</th><th>Risk</th><th>Readability</th><th>Composite</th><th>Recommendation</th></tr>" + score_rows + "</table>" if score_rows else ""}

      <div class="section-label">Code diff (original → optimized)</div>
      <pre>{diff_html}</pre>
    </div>
    """


def generate_report():
    sections = []
    summary_rows = ""

    for filepath, args, description in EXAMPLES:
        print(f"\nRunning pipeline for: {description}")
        with open(filepath) as f:
            original_code = f.read()

        result = run_pipeline(filepath, args)
        sections.append(_render_example(description, filepath, original_code, result))

        if result["success"]:
            summary_rows += f"""
              <tr>
                <td>{html.escape(description)}</td>
                <td><span class="speedup" style="font-size:14px">{result['benchmark']['speedup']}x</span></td>
                <td>{result['rounds']}</td>
                <td>{result.get('score', {}).get('composite_score', '—')}</td>
              </tr>
            """
        else:
            summary_rows += f"""
              <tr>
                <td>{html.escape(description)}</td>
                <td colspan="3" style="color: var(--red)">FAILED after {result['rounds']} round(s)</td>
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

    print(f"\n✅ Report generated: {REPORT_PATH}")


if __name__ == "__main__":
    generate_report()
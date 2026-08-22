"""model -> single self-contained HTML, via Jinja2. CSS+JS are already
inlined inside template.html.j2; this module's only job is to embed the
run model as JSON and return the finished markup. Kept separate from
builder.py so the model stays unit-testable without touching Jinja at all.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATE_NAME = "template.html.j2"


def render_html(run_model: dict) -> str:
    """Render a run model (see builder.build_run_model) to a self-contained
    report.html string. No network calls, no external assets besides the
    Google Fonts stylesheet link.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
    )
    template = env.get_template(_TEMPLATE_NAME)

    # Embed as JSON inside a <script type="application/json"> tag: escape
    # "</" so a literal "</script>" inside any string value (a body, a url)
    # can't prematurely close the tag and break the page.
    run_json = json.dumps(run_model, default=str).replace("</", "<\\/")

    return template.render(run_json=run_json, meta=run_model.get("meta", {}))


def render_index_html(env: str, history: list[dict]) -> str:
    """A small, self-contained per-environment index: every run in the
    current history window (see core.report.builder), newest first, each
    linking to its own report.html -- the one stable entry point so you
    don't have to know a run's timestamped folder name to find it.
    Regenerated fresh on every run from the same history.json the report's
    own history chart reads, so the two never disagree.
    """
    rows = []
    for h in sorted(history, key=lambda r: r["run"], reverse=True):
        folder = h.get("folder")
        total = h["passed"] + h["failed"] + h["skipped"]
        pass_rate = f"{round(100 * h['passed'] / total)}%" if total else "—"
        link = (
            f'<a class="view" href="./{html.escape(folder)}/report.html">View report →</a>'
            if folder else '<span class="view disabled">no report (pre-existing run)</span>'
        )
        rows.append(f"""
        <tr>
          <td class="mono">#{h['run']}</td>
          <td class="mono">{html.escape(folder) if folder else '—'}</td>
          <td><span class="pill pass">{h['passed']} pass</span></td>
          <td><span class="pill fail">{h['failed']} fail</span></td>
          <td><span class="pill skip">{h['skipped']} skip</span></td>
          <td class="mono">{pass_rate}</td>
          <td class="mono">{h.get('durationMs', 0) / 1000:.1f}s</td>
          <td>{link}</td>
        </tr>""")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(env)} — run history</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #f6f6f3; --surface: #ffffff; --ink: #17181c; --muted: #5c626b; --line: #e6e6e1;
  --ok: #0f7a52; --ok-tint: #e3f3ea; --bad: #c0341d; --bad-tint: #fbe9e5; --warn: #a3690f; --warn-tint: #f8eddc;
  --font-sans: "IBM Plex Sans", -apple-system, "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, "SF Mono", Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0e1013; --surface: #15181d; --ink: #e9ebee; --muted: #9aa1ab; --line: #262b33;
    --ok: #34c88d; --ok-tint: #113127; --bad: #f06a52; --bad-tint: #35201d; --warn: #e3ad4c; --warn-tint: #332812;
  }}
}}
* {{ box-sizing: border-box; }}
html {{ color-scheme: light dark; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: var(--font-sans); font-size: 14px; line-height: 1.5; }}
.wrap {{ max-width: 1040px; margin: 0 auto; padding: 48px 40px 64px; }}
.mono {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
h1 {{ font-size: 20px; font-weight: 600; margin: 0 0 4px; }}
.sub {{ color: var(--muted); font-size: 13px; margin: 0 0 28px; }}
.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,.04); }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); font-weight: 600; padding: 12px 16px; border-bottom: 1px solid var(--line); }}
td {{ padding: 12px 16px; border-bottom: 1px solid var(--line); vertical-align: middle; }}
tr:last-child td {{ border-bottom: none; }}
.pill {{ display: inline-block; font-family: var(--font-mono); font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 999px; }}
.pill.pass {{ background: var(--ok-tint); color: var(--ok); }}
.pill.fail {{ background: var(--bad-tint); color: var(--bad); }}
.pill.skip {{ background: var(--warn-tint); color: var(--warn); }}
.view {{ color: var(--ok); text-decoration: none; font-size: 13px; font-weight: 500; }}
.view:hover {{ text-decoration: underline; }}
.view.disabled {{ color: var(--muted); font-weight: 400; }}
.empty {{ padding: 40px; text-align: center; color: var(--muted); }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{html.escape(env)} — run history</h1>
  <p class="sub">Last {len(history)} run(s). Regenerated on every test run.</p>
  <div class="card">
    {"<table><thead><tr><th>Run</th><th>Timestamp</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Pass rate</th><th>Duration</th><th></th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>" if rows else '<div class="empty">No runs recorded yet.</div>'}
  </div>
</div>
</body>
</html>
"""

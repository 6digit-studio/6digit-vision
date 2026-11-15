#!/usr/bin/env python3
"""Render the experiment markdown into the styled HTML pages used on Pages.

The live site serves .md as text/markdown (raw), which hides the embedded
outputs. This produces REPORT.html / TOOL_USAGE.html / the discipline page with
the same dark chrome as the galleries.

Run: uv run --with markdown python ab_runs/render_reports.py
"""
import html
import pathlib
import re

import markdown

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent

DOCS = [
    (ROOT / "REPORT.md", ROOT / "REPORT.html", "A/B/C report"),
    (ROOT / "TOOL_USAGE.md", ROOT / "TOOL_USAGE.html", "Tool usage audit"),
    (REPO / "docs" / "MEASUREMENT_DISCIPLINE.md",
     REPO / "docs" / "MEASUREMENT_DISCIPLINE.html", "Measurement discipline"),
]

CSS = """
:root { --bg:#0d1117; --panel:#161b22; --border:#30363d; --fg:#e6edf3;
        --dim:#8b949e; --accent:#58a6ff; }
* { box-sizing:border-box; }
body { background:var(--bg); color:var(--fg); margin:0;
       font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }
.wrap { max-width:1080px; margin:0 auto; padding:40px 28px 72px; }
nav { font:12px/1.5 -apple-system,"SF Mono",Menlo,monospace; color:var(--dim);
      border-bottom:1px solid var(--border); padding-bottom:14px; margin-bottom:30px; }
nav a { color:var(--accent); text-decoration:none; margin-right:14px; }
nav a:hover { text-decoration:underline; }
h1 { font-size:30px; line-height:1.2; margin:0 0 18px; letter-spacing:-.01em; }
h2 { font-size:21px; margin:42px 0 12px; padding-bottom:6px; border-bottom:1px solid var(--border); }
h3 { font-size:16px; margin:28px 0 8px; color:#cdd5df; }
p, li { color:#cfd6df; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
strong { color:#fff; }
code { font:0.88em/1.4 "SF Mono",Menlo,monospace; background:#0b0f14;
       padding:1px 5px; border-radius:4px; color:#c9d1d9; }
pre { background:#0b0f14; border:1px solid var(--border); border-radius:8px;
      padding:14px 16px; overflow:auto; }
pre code { background:none; padding:0; }
img { max-width:100%; height:auto; display:block; margin:16px 0 8px;
      border:1px solid var(--border); border-radius:8px; background:#000; }
table { border-collapse:collapse; width:100%; margin:14px 0 22px; font-size:13px; }
th, td { border-bottom:1px solid var(--border); padding:7px 9px; text-align:left; }
th { color:var(--dim); font-weight:600; }
blockquote { margin:16px 0; padding:4px 0 4px 16px; border-left:3px solid var(--border); color:var(--dim); }
hr { border:0; border-top:1px solid var(--border); margin:34px 0; }
.foot { color:#6e7681; font-size:11px; margin-top:48px; border-top:1px solid var(--border); padding-top:14px; }
.foot code { background:none; padding:0; color:#6e7681; }
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — 6digit-vision</title>
<style>{css}</style></head>
<body><div class="wrap">
<nav>
  <a href="../MIMICRY_GALLERY.html">← gallery</a>
  <a href="../ab_runs/REPORT.html">report</a>
  <a href="../ab_runs/TOOL_USAGE.html">tool usage</a>
  <a href="../docs/MEASUREMENT_DISCIPLINE.html">discipline</a>
  <a href="https://github.com/6digit-studio/6digit-vision">github</a>
</nav>
{body}
<div class="foot">Rendered from <code>{source}</code> · regenerate with
<code>uv run --with markdown python ab_runs/render_reports.py</code></div>
</div></body></html>
"""


def render(src: pathlib.Path, dst: pathlib.Path, label: str) -> None:
    text = src.read_text()
    m = re.match(r"#\s+(.+)", text)
    title = m.group(1).strip() if m else label
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list", "toc"],
    )
    # live pages for the sibling docs, not raw markdown
    body = re.sub(r'href="([^"]+)\.md"', r'href="\1.html"', body)
    out = TEMPLATE.format(title=html.escape(title), css=CSS, body=body,
                          source=src.name)
    dst.write_text(out)
    print("wrote", dst.relative_to(REPO))


for src, dst, label in DOCS:
    render(src, dst, label)

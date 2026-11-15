#!/usr/bin/env python3
"""Static HTML gallery from results.json + cell artifacts."""
import json, pathlib, html

ROOT = pathlib.Path(__file__).resolve().parent
REFS = [("ref1-collage", "KODOR collage", "1520×794 · UI screens, real typography"),
        ("ref2-knob", "Knob / keycap", "438×393 · 3D product render, teal rim light"),
        ("ref3-bp", "BP widget", "394×210 · dark UI, pink ECG + glow"),
        ("ref4-flight", "Flight card", "400×155 · dark UI, turquoise progress line")]
ARMS = [a for a in ["A", "B", "C"] if (ROOT / a).exists()]
ARM_DESC = {"A": "vision only", "B": "vision + interrogate facts", "C": "vision + live score/pixdiff/zoom"}
data = json.loads((ROOT / "results.json").read_text())
res = {(r["ref"], r["arm"]): r for r in data["rows"]}

def verdict(slug, arm):
    p = ROOT / arm / slug / "VERDICT.md"
    if not p.exists():
        return ""
    return html.escape(p.read_text().strip())

rows = []
for slug, name, sub in REFS:
    cells = []
    for arm in ["ref"] + ARMS:
        if arm == "ref":
            cells.append(f'<figure><img src="A/{slug}/reference.png"><figcaption>REFERENCE</figcaption></figure>')
            continue
        r = res.get((slug, arm))
        if not r:
            continue
        c = r["components"]
        bar = (f'<span class="m">SSIM <b>{r["ssim"]:.3f}</b></span>'
               f'<span class="m">mismatch <b>{r["mismatch"]*100:.1f}%</b></span>'
               f'<span class="m">RMSE <b>{r["rmse"]:.3f}</b></span>'
               f'<span class="m">score <b>{r["score"]:.1f}</b>/{r["ceiling"]:.1f}</span>')
        comp = " · ".join(f'{k} {v:.2f}' for k, v in c.items())
        cells.append(f'<figure><img src="{arm}/{slug}/candidate.png">'
                     f'<figcaption>ARM {arm} — {ARM_DESC[arm]}</figcaption>'
                     f'<div class="metrics">{bar}</div><div class="comp">{comp}</div></figure>')
    rows.append(f'<section><h2>{name}</h2><div class="sub">{sub}</div>'
                f'<div class="pair">{"".join(cells)}</div></section>')

table = ["<table><tr><th>reference</th><th>arm</th><th>SSIM↑</th><th>mismatch↓</th>"
         "<th>RMSE↓</th><th>score</th><th>self-est</th></tr>"]
for slug, name, _ in REFS:
    for arm in ARMS:
        r = res.get((slug, arm))
        if not r:
            continue
        table.append(f'<tr><td>{name}</td><td>{arm} — {ARM_DESC[arm]}</td>'
                     f'<td>{r["ssim"]:.3f}</td><td>{r["mismatch"]*100:.1f}%</td>'
                     f'<td>{r["rmse"]:.3f}</td><td>{r["score"]:.1f}/{r["ceiling"]:.1f}</td>'
                     f'<td>{r["self_estimate"] if r["self_estimate"] is not None else "—"}</td></tr>')
table.append("</table>")
ceil = " · ".join(f'{k} {v}' for k, v in data["ceilings"].items())

page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>eyes A/B — does the instrument add anything?</title>
<style>
:root{{--bg:#0d1117;--panel:#161b22;--border:#30363d;--fg:#e6edf3;--dim:#8b949e;--accent:#58a6ff;--good:#3fb950}}
*{{box-sizing:border-box}} body{{background:var(--bg);color:var(--fg);font:14px/1.55 -apple-system,BlinkMacSystemFont,"SF Mono",Menlo,monospace;margin:0;padding:36px}}
h1{{font-size:22px;margin:0 0 6px}} h2{{font-size:16px;margin:0 0 2px}} .sub{{color:var(--dim);font-size:12px;margin-bottom:14px}}
.lead{{color:var(--dim);max-width:900px;margin-bottom:26px}} .lead b{{color:var(--fg)}}
section{{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:18px;margin-bottom:22px}}
.pair{{display:flex;gap:14px;flex-wrap:wrap}} figure{{margin:0;flex:1 1 260px;min-width:240px}}
img{{width:100%;display:block;border:1px solid var(--border);border-radius:6px;background:#000}}
figcaption{{color:var(--dim);font-size:11px;letter-spacing:.06em;text-transform:uppercase;margin-top:7px}}
.metrics{{display:flex;gap:10px;flex-wrap:wrap;margin-top:5px;font-size:11px;color:var(--dim)}}
.metrics b{{color:var(--fg)}} .comp{{color:#6e7681;font-size:10px;margin-top:2px}}
table{{border-collapse:collapse;width:100%;font-size:12px;margin:14px 0 26px}}
th,td{{border-bottom:1px solid var(--border);padding:7px 9px;text-align:left}} th{{color:var(--dim);font-weight:600}}
code{{background:#0b0f14;padding:1px 5px;border-radius:4px}}
.note{{border-left:3px solid var(--border);padding-left:12px;color:var(--dim);font-size:12px}}
</style></head><body>
<h1>Does <code>eyes</code> add anything?</h1>
<div class="lead">Four references × three sensing modes, same model, same renderer, isolated workspaces.
<b>A</b> is vision only. <b>B</b> adds the precomputed <code>interrogate</code> fact sheet. <b>C</b> adds the live
<code>score</code>/<code>pixdiff</code>/<code>zoom</code> loop. SSIM and RMSE are pixel truth; <code>score</code> is semantic and
normalized against each reference's self-ceiling ({ceil}).</div>
{table}
{''.join(rows)}
<div class="note">Self-ceiling is the score an identical image receives — the palette component tops out at
top-8-bin coverage, so 100 is unreachable (see REPORT.md).</div>
</body></html>"""
(ROOT / "gallery.html").write_text(page)
print("saved", ROOT / "gallery.html")

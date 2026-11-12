"""Builds UPI_Dashboard.html: one self-contained file (data and d3 embedded) that opens offline by double-click.
Run build_dashboard_data.py first, then this. Downloads d3 v7.8.5 on the first run if d3.min.js is missing.
Also copies the result to ..\..\docs\index.html, which GitHub Pages serves."""
import json
import os
import re
import shutil
import urllib.request

HERE = "."
D3_URL = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"
if not os.path.exists(rf"{HERE}\d3.min.js"):
    urllib.request.urlretrieve(D3_URL, rf"{HERE}\d3.min.js")
page = open(rf"{HERE}\index.html", encoding="utf-8").read()
d3 = open(rf"{HERE}\d3.min.js", encoding="utf-8").read()
data = {k: json.load(open(rf"{HERE}\{f}.json", encoding="utf-8")) for k, f in
        (("master", "master"), ("brands", "brand_share"), ("forecast", "forecast"), ("backtest", "backtest"), ("events", "events"))}

style = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
markup = page[page.index("</style>") + len("</style>"): page.index("<script>")].strip()
script = re.search(r"<script>(.*)</script>", page, re.S).group(1)

TOKENS = """
:root {
  color-scheme: light;
  --color-bg: #fcfcfb; --color-panel: #f4f3f0; --color-fg: #0b0b0b; --color-fg-muted: #5f5e5a; --cds-text-secondary: #52514e;
  --color-border-line: #e1e0d9; --cds-border: rgba(11,11,11,.12); --cds-surface-popover: #ffffff; --cds-shadow-popover: 0 6px 20px rgba(0,0,0,.14);
  --cds-chart-grid: #e1e0d9; --cds-chart-axis: #c3c2b7; --cds-chart-reference: #898781; --cds-chart-muted: #898781;
  --color-ok: #006300; --color-warn: #8a5a00; --color-bad: #d03b3b;
  --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a; --series-4: #eda100; --series-5: #e87ba4; --series-6: #008300; --series-7: #6250d6; --series-8: #e34948;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  color-scheme: dark;
  --color-bg: #1a1a19; --color-panel: #232321; --color-fg: #f0efec; --color-fg-muted: #a9a89f; --cds-text-secondary: #c3c2b7;
  --color-border-line: #2c2c2a; --cds-border: rgba(255,255,255,.14); --cds-surface-popover: #262624; --cds-shadow-popover: 0 6px 20px rgba(0,0,0,.5);
  --cds-chart-grid: #2c2c2a; --cds-chart-axis: #383835; --cds-chart-reference: #898781; --cds-chart-muted: #898781;
  --color-ok: #0ca30c; --color-warn: #fab219; --color-bad: #e66767;
  --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500; --series-5: #d55181; --series-6: #008300; --series-7: #9085e9; --series-8: #e66767;
} }
:root[data-theme="dark"] {
  color-scheme: dark;
  --color-bg: #1a1a19; --color-panel: #232321; --color-fg: #f0efec; --color-fg-muted: #a9a89f; --cds-text-secondary: #c3c2b7;
  --color-border-line: #2c2c2a; --cds-border: rgba(255,255,255,.14); --cds-surface-popover: #262624; --cds-shadow-popover: 0 6px 20px rgba(0,0,0,.5);
  --cds-chart-grid: #2c2c2a; --cds-chart-axis: #383835; --cds-chart-reference: #898781; --cds-chart-muted: #898781;
  --color-ok: #0ca30c; --color-warn: #fab219; --color-bad: #e66767;
  --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500; --series-5: #d55181; --series-6: #008300; --series-7: #9085e9; --series-8: #e66767;
}
:root {
  --font-anthropic-sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; --font-anthropic-serif: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --cds-font-size-caption: 12.5px; --cds-font-size-body: 14px; --cds-font-size-heading: 19px; --cds-font-size-title: 26px; --cds-font-weight-medium: 600;
  --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 12px; --cds-gap-lg: 18px; --cds-gap-xl: 34px;
  --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 12px; --cds-pad-lg: 16px; --cds-pad-xl: 24px; --cds-radius: 10px;
}
html { background: var(--color-bg); }
body { margin: 0; background: var(--color-bg); color: var(--color-fg); font: 14px/1.4 var(--font-anthropic-sans); }
.u-main { max-width: 1120px; margin: 0 auto; padding: 28px max(16px, env(safe-area-inset-left, 0px)) 48px; }
.u-page h1 { font-weight: 650; letter-spacing: -0.02em; font-size: 30px; }
.u-kpi .v { font-weight: 650; letter-spacing: -0.02em; }
.dash-select { background-color: var(--color-panel); color: var(--color-fg); border: 1px solid var(--color-border-line); border-radius: 6px; padding: 4px 8px; font: inherit; }
@media (prefers-reduced-motion: no-preference) { .u-tip { transition: opacity .12s; } }
"""

SHIM = """
window.dash = (function () {
  const calcs = {}, draws = {}, cache = {};
  const colors = [1, 2, 3, 4, 5, 6, 7, 8].map((i) => 'var(--series-' + i + ')');
  function data(id) {
    if (calcs[id]) {
      if (!(id in cache)) cache[id] = calcs[id].fn.apply(null, calcs[id].inputs.map((i) => data(i).data));
      return {status: 'ok', data: cache[id]};
    }
    return window.__DATA__[id] ? {status: 'ok', data: window.__DATA__[id]} : {status: 'missing', data: []};
  }
  function draw(name, fn) {
    if (typeof fn === 'function') { draws[name] = fn; return; }
    document.querySelectorAll('[data-draw="' + name + '"]').forEach((el) => { try { draws[name](el); } catch (e) { console.error(name, e); } });
  }
  return {colors, data, calc: (id, o) => { calcs[id] = o; }, draw, runAll: () => Object.keys(draws).forEach((n) => draw(n))};
})();
"""

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UPI Market Dashboard</title>
<style>{TOKENS}</style>
<style>{style}</style>
</head>
<body>
<main class="u-main">
{markup}
</main>
<script>{d3}</script>
<script>window.__DATA__ = {json.dumps(data, ensure_ascii=False, separators=(",", ":"))};{SHIM}</script>
<script>{script}</script>
<script>
dash.runAll();
let _t; window.addEventListener('resize', () => {{ clearTimeout(_t); _t = setTimeout(() => dash.runAll(), 120); }});
</script>
</body>
</html>
"""
with open(rf"{HERE}\UPI_Dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
os.makedirs(r"..\..\docs", exist_ok=True)
shutil.copy(rf"{HERE}\UPI_Dashboard.html", r"..\..\docs\index.html")
print("wrote UPI_Dashboard.html and docs/index.html", round(len(html) / 1024), "KB")

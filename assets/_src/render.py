"""Render elegant code-window PNGs for the README.

Each scene is an HTML document: a macOS-style code window floating on a layered
CSS gradient. Playwright (Chromium) screenshots the framed element to PNG at 2x
for crisp retina output.

Run:  uv run python assets/_src/render.py
"""

from __future__ import annotations

import pathlib

from playwright.sync_api import sync_playwright

OUT = pathlib.Path(__file__).resolve().parent.parent

# --- syntax-highlight helpers ------------------------------------------------
# Tiny hand-rolled tokenless highlighter: we just wrap spans by hand in the
# snippets so the colours are exactly what we want, no parser surprises.


def page(title: str, gradient: str, accent: str, body: str, pad: int = 90) -> str:
    """A full HTML doc: gradient stage + a single framed code window."""
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html,body {{ background:#0b0b12; }}
  .stage {{
    width: 1200px; padding: {pad}px;
    background: {gradient};
    display:flex; align-items:center; justify-content:center;
    position:relative; overflow:hidden;
  }}
  .stage::before {{
    content:""; position:absolute; inset:0;
    background:
      radial-gradient(60% 50% at 18% 12%, rgba(255,255,255,.18), transparent 60%),
      radial-gradient(45% 40% at 88% 90%, rgba(0,0,0,.28), transparent 60%);
    pointer-events:none;
  }}
  .win {{
    width: 100%; border-radius: 16px; overflow:hidden;
    background: rgba(18,18,28,.92);
    backdrop-filter: blur(12px);
    box-shadow:
      0 1px 0 rgba(255,255,255,.10) inset,
      0 40px 80px -20px rgba(0,0,0,.65),
      0 8px 24px -8px rgba(0,0,0,.5);
    border: 1px solid rgba(255,255,255,.08);
    position:relative; z-index:1;
  }}
  .bar {{
    height: 46px; display:flex; align-items:center; gap:8px;
    padding: 0 18px;
    background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.01));
    border-bottom: 1px solid rgba(255,255,255,.06);
  }}
  .dot {{ width:13px; height:13px; border-radius:50%; }}
  .r {{ background:#ff5f57; }} .y {{ background:#febc2e; }} .g {{ background:#28c840; }}
  .title {{
    margin-left: 14px; color: rgba(255,255,255,.55);
    font: 600 13px Inter, sans-serif; letter-spacing:.2px;
  }}
  .badge {{
    margin-left:auto; font: 700 11px Inter, sans-serif; letter-spacing:.6px;
    color:{accent}; padding:4px 10px; border-radius:999px;
    background: rgba(255,255,255,.06); border:1px solid {accent}33;
    text-transform:uppercase;
  }}
  pre {{
    margin:0; padding: 26px 30px 30px;
    font: 500 18px/1.7 'JetBrains Mono', monospace;
    color:#c9d1d9; tab-size:2; white-space:pre;
  }}
  .c  {{ color:#6a7a8c; font-style:italic; }}   /* comment  */
  .k  {{ color:#ff7b9c; }}                        /* keyword  */
  .s  {{ color:#7ee787; }}                        /* string   */
  .n  {{ color:#79c0ff; }}                        /* number   */
  .f  {{ color:#d2a8ff; }}                        /* func     */
  .a  {{ color:#ffa657; }}                        /* attr/sym */
  .t  {{ color:#56d4dd; }}                        /* type     */
  .ok {{ color:#3fb950; font-weight:700; }}
  .er {{ color:#ff7b72; font-weight:700; }}
  .dim {{ color:#7d8590; }}
</style></head>
<body>
  <div class="stage">
    <div class="win">
      <div class="bar">
        <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
        <span class="title">{title}</span>
        <span class="badge">qvalidate</span>
      </div>
      <pre>{body}</pre>
    </div>
  </div>
</body></html>"""


# --- scenes ------------------------------------------------------------------

HERO = page(
    title="validate.py — pass/fail in one call",
    gradient="linear-gradient(135deg,#6366f1 0%,#8b5cf6 38%,#d946ef 72%,#f0abfc 100%)",
    accent="#d2a8ff",
    body=(
        '<span class="k">from</span> qvalidate <span class="k">import</span> validate\n\n'
        '<span class="c"># Hand the agent\'s generated q query straight in.</span>\n'
        'r = <span class="f">validate</span>(<span class="s">"select px, sz from trades where sym=`AAPL"</span>)\n\n'
        'r.valid                      <span class="c"># </span><span class="ok">True</span>\n'
        'r.diagnostics                <span class="c"># </span><span class="dim">[]</span>\n'
        'r.metadata.sql[<span class="n">0</span>]            <span class="c"># </span>'
        '<span class="t">SqlBlock</span>(op=<span class="s">\'select\'</span>, '
        'table=<span class="s">\'trades\'</span>,\n'
        '                             <span class="c">#          </span>'
        'columns=[<span class="s">\'px\'</span>,<span class="s">\'sz\'</span>,<span class="s">\'sym\'</span>])\n'
        'r.metadata.references        <span class="c"># </span>'
        '[<span class="s">\'px\'</span>, <span class="s">\'sz\'</span>, '
        '<span class="s">\'trades\'</span>, <span class="s">\'sym\'</span>]'
    ),
)

SELFCORRECT = page(
    title="self_correct.py — the agentic feedback loop",
    gradient="linear-gradient(135deg,#0ea5e9 0%,#2563eb 40%,#4f46e5 75%,#7c3aed 100%)",
    accent="#56d4dd",
    body=(
        '<span class="c"># The LLM emitted a query — gate it before it ever hits kdb+.</span>\n'
        'r = <span class="f">validate</span>(<span class="s">"select px, sz where sym=`AAPL"</span>)\n\n'
        '<span class="k">if</span> <span class="k">not</span> r.valid:\n'
        '    <span class="c"># Feed the structured diagnostic back to the model.</span>\n'
        '    d = r.diagnostics[<span class="n">0</span>]\n'
        '    <span class="f">print</span>(<span class="s">f"</span><span class="er">{d.code}</span><span class="s">: {d.message} @ {d.line}:{d.column}"</span>)\n\n'
        '<span class="dim">>>> </span><span class="er">QSQL_MISSING_FROM</span><span class="dim">: qSQL \'select\' statement is missing a \'from\' clause. @ 1:1</span>\n'
        '<span class="dim">>>> </span><span class="c"># agent regenerates → validate() → </span><span class="ok">True</span><span class="c"> → run.  No round-trip to a live session.</span>'
    ),
)

METADATA = page(
    title="tool_output.py — JSON-ready, zero glue",
    gradient="linear-gradient(135deg,#059669 0%,#0d9488 42%,#0891b2 78%,#22d3ee 100%)",
    accent="#7ee787",
    body=(
        '<span class="k">import</span> dataclasses, json\n'
        '<span class="k">from</span> qvalidate <span class="k">import</span> validate\n\n'
        'r = <span class="f">validate</span>(<span class="s">"</span><span class="a">.util.add</span><span class="s">:{[x;y] x+y}; .util.add[2;3]"</span>)\n\n'
        '<span class="c"># Every result is a plain dataclass → drop it into any tool schema.</span>\n'
        'json.<span class="f">dumps</span>(dataclasses.<span class="f">asdict</span>(r))\n\n'
        '<span class="dim">{</span>\n'
        '  <span class="s">"valid"</span>: <span class="ok">true</span>,\n'
        '  <span class="s">"diagnostics"</span>: <span class="dim">[]</span>,\n'
        '  <span class="s">"metadata"</span>: <span class="dim">{</span> <span class="s">"defined_symbols"</span>: [<span class="s">"</span><span class="a">.util.add</span><span class="s">"</span>, <span class="s">"y"</span>, <span class="s">"x"</span>],\n'
        '                 <span class="s">"references"</span>: [<span class="s">"</span><span class="a">.util.add</span><span class="s">"</span>, <span class="s">"x"</span>, <span class="s">"y"</span>],\n'
        '                 <span class="s">"namespaces"</span>: <span class="dim">[]</span>, <span class="s">"sql"</span>: <span class="dim">[]</span> <span class="dim">}</span>\n'
        '<span class="dim">}</span>'
    ),
)

SCENES = {
    "hero.png": HERO,
    "self-correct.png": SELFCORRECT,
    "metadata.png": METADATA,
}


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(device_scale_factor=2)
        for name, html in SCENES.items():
            pg.set_content(html, wait_until="networkidle")
            pg.wait_for_timeout(350)  # let webfonts settle
            stage = pg.query_selector(".stage")
            assert stage is not None
            stage.screenshot(path=str(OUT / name))
            print(f"wrote {name}")
        browser.close()


if __name__ == "__main__":
    main()

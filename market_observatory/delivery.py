"""Bundled demo and portable reports."""

import csv
import html
import io
import json
import os
import tempfile
from importlib.resources import files
from pathlib import Path

from .engine import parse_csv


def demo_dataset():
    root = files("market_observatory").joinpath("data")
    return parse_csv(
        root.joinpath("demo.csv").read_bytes().decode("utf-8"),
        json.loads(root.joinpath("demo.json").read_text(encoding="utf-8")),
    )


def csv_report(result):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    symbols = result["settings"]["symbols"]
    writer.writerow(
        ["date", "portfolio_value", "portfolio_growth", "portfolio_drawdown"]
        + [f"{s}_{kind}" for s in symbols for kind in ["close", "return", "growth", "drawdown"]]
    )
    for i, day in enumerate(result["dates"]):
        row = [day] + [
            result["series"][key][i]
            for key in ["portfolio_value", "portfolio_growth", "portfolio_drawdown"]
        ]
        for symbol in symbols:
            row.extend(
                result["series"][key][symbol][i]
                for key in ["prices", "returns", "growth", "drawdown"]
            )
        writer.writerow(row)
    return output.getvalue()


def html_report(result):
    def escape(value):
        return html.escape(str(value), quote=True)

    def percent(value):
        return "Undefined" if value is None else f"{value:.2%}"

    rows = "".join(
        "<tr><th>"
        + escape(row["symbol"])
        + "</th>"
        + "".join(
            "<td>" + percent(row[k]) + "</td>"
            for k in ["total_return", "cagr", "annualized_volatility", "max_drawdown"]
        )
        + "</tr>"
        for row in [{"symbol": "Portfolio", **result["portfolio"]}] + result["assets"]
    )
    meta = "".join(
        f"<dt>{escape(k.replace('_', ' ').title())}</dt><dd>{escape(v)}</dd>"
        for k, v in result["metadata"].items()
    )
    warnings = "".join("<li>" + escape(w) + "</li>" for w in result["warnings"])
    details = escape(
        json.dumps(
            {
                "settings": result["settings"],
                "provenance": result["provenance"],
                "coverage": result["coverage"],
                "engine_version": result["engine_version"],
            },
            indent=2,
            allow_nan=False,
        )
    )
    points = result["series"]["portfolio_growth"]
    # Report plot is bounded for large imports while full series remains in JSON/CSV.
    stride = max(1, (len(points) - 1) // 800)
    indices = sorted(set(range(0, len(points), stride)) | {len(points) - 1})
    low, high = min(points), max(points)
    spread = high - low or 1
    path = " ".join(
        f"{'M' if j == 0 else 'L'}{40 + 720 * i / (len(points) - 1):.2f},{200 - 160 * (points[i] - low) / spread:.2f}"
        for j, i in enumerate(indices)
    )
    title = escape(result["metadata"]["title"])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | MarketObservatory</title><style>
:root{{color-scheme:dark;--page:#0d1015;--surface:#151a22;--ink:#edf1f7;--muted:#aab5c6;--line:#3c485b;--accent:#93baff;font:15px/1.55 system-ui,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--page);color:var(--ink)}}.report{{max-width:1440px;margin:auto;padding:28px 32px 40px}}.report-header{{padding:0 0 24px;border-bottom:1px solid var(--line)}}small{{display:block;font-size:13px;font-weight:650;color:var(--accent)}}h1{{font-size:clamp(25px,3vw,34px);font-weight:550;letter-spacing:-.8px;line-height:1.2;margin:14px 0 10px}}.report-meta{{font:12px/1.7 ui-monospace,monospace;font-variant-numeric:tabular-nums;color:var(--muted);margin:0}}h2{{font-size:17px;font-weight:600;margin:0 0 16px;letter-spacing:-.2px}}p{{margin:12px 0;color:var(--muted);font-size:13px}}strong{{color:var(--ink)}}.report-grid{{display:grid;grid-template-columns:minmax(0,1fr) 300px;grid-template-areas:"growth context" "metrics context" "reproduction reproduction";column-gap:28px;row-gap:24px;padding-top:24px}}.growth{{grid-area:growth;min-width:0}}.metrics{{grid-area:metrics;min-width:0}}.context{{grid-area:context;border-left:1px solid var(--line);padding-left:24px;min-width:0}}.reproduction{{grid-area:reproduction;min-width:0;border-top:1px solid var(--line);padding-top:24px}}.context h2:not(:first-child){{margin-top:28px}}.growth svg{{display:block;width:100%;background:var(--surface);border-block:1px solid var(--line)}}.growth svg path{{stroke:var(--accent)}}.growth svg text{{fill:var(--muted);font:14px ui-monospace,monospace}}.growth p{{font-size:12px;line-height:1.7;margin-bottom:0}}.table-scroll{{max-width:100%;overflow-x:auto;overscroll-behavior-inline:contain;border:1px solid var(--line);background:var(--surface)}}table{{border-collapse:collapse;width:100%;min-width:620px;font-size:12px;font-variant-numeric:tabular-nums}}th,td{{text-align:right;padding:12px;border-bottom:1px solid var(--line);white-space:nowrap}}thead th{{font-size:11px;font-weight:500;color:var(--muted);white-space:normal;line-height:1.4}}th:first-child{{text-align:left}}tbody th{{font-size:12px;font-weight:500}}td{{font-family:ui-monospace,monospace}}tbody tr:first-child{{background:#1e2b40}}tbody tr:first-child th,tbody tr:first-child td{{color:#bed4ff;font-weight:650}}tbody tr:last-child th,tbody tr:last-child td{{border-bottom:0}}.table-hint{{display:none}}details{{margin-top:14px;font-size:13px}}summary{{cursor:pointer;color:var(--accent);padding:4px 0;min-height:30px}}summary:focus-visible,.table-scroll:focus-visible,pre:focus-visible{{outline:2px solid var(--accent);outline-offset:4px}}details dl{{margin-top:14px}}dt{{font-size:12px;font-weight:600;color:var(--muted);margin-bottom:3px}}dd{{font-size:12px;margin:0 0 16px;overflow-wrap:anywhere}}ul{{padding-left:18px;margin:0}}li{{font-size:12px;color:var(--muted);margin-bottom:12px;line-height:1.65}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;max-height:400px;overflow:auto;margin:0;padding:20px 24px;border:1px solid var(--line);background:var(--surface);font:12px/1.7 ui-monospace,monospace;color:#c4d1e4;tab-size:2}}.reproduction>p{{font-size:12px}}
@media(max-width:1100px){{.report-grid{{grid-template-columns:minmax(0,1fr) 250px;column-gap:20px}}.context{{padding-left:20px}}.table-hint{{display:block;font-size:12px;margin:0 0 10px}}}}
@media(max-width:900px){{.report-grid{{grid-template-columns:1fr;grid-template-areas:"growth" "metrics" "context" "reproduction"}}.context{{border-left:0;border-top:1px solid var(--line);padding:24px 0 0;display:grid;grid-template-columns:1fr 1fr;gap:24px}}.context h2:not(:first-child){{margin-top:0}}}}
@media(max-width:600px){{.report{{padding:24px 16px}}.report-header{{padding-bottom:20px}}h1{{font-size:27px}}.report-grid{{padding-top:20px;row-gap:24px}}.report-meta{{font-size:11px}}small{{font-size:12px}}.growth svg{{min-height:150px}}.growth svg text{{font-size:28px}}.context{{display:block}}.context h2:not(:first-child){{margin-top:24px}}pre{{padding:16px;max-height:400px}}.table-hint{{display:block}}th,td{{padding:12px 10px}}}}
@media print{{:root{{color-scheme:light;--page:white;--surface:white;--ink:#111827;--muted:#374151;--line:#a0a8b3;--accent:#1d4ed8}}body{{margin:0}}.report{{padding:16px;max-width:none}}.report-grid{{display:block}}.report-grid>section{{margin:0 0 24px}}.context{{display:block;border:0;padding:0}}.context h2:not(:first-child){{margin-top:24px}}.table-scroll{{overflow:visible}}table{{min-width:0;font-size:10px}}thead th{{font-size:10px}}th,td{{padding:8px}}tbody tr:first-child{{background:#eef2f7}}tbody tr:first-child th,tbody tr:first-child td{{color:#111827}}.growth svg text{{fill:#374151}}pre{{max-height:none;overflow:visible;color:#111827;background:white;break-inside:auto}}.table-hint{{display:none}}}}
</style><body><div class="report"><header class="report-header"><small>MARKETOBSERVATORY · PORTFOLIO ANALYSIS</small><h1>{title}</h1><p class="report-meta">{result["dates"][0]} to {result["dates"][-1]} · {len(points)} aligned observations · {escape(result["settings"]["mode"])}</p></header><main class="report-grid"><section class="growth" aria-labelledby="growth-title"><h2 id="growth-title">Portfolio growth</h2><svg viewBox="0 0 800 240" role="img" aria-label="Historical portfolio growth"><path d="{path}" fill="none" stroke="#146579" stroke-width="3"/><text x="40" y="225">Start: 1.000</text><text x="620" y="225">End: {points[-1]:.3f}</text></svg><p><strong>Read the curve:</strong> 1.000 is the starting value. A value of 1.100 means 10% growth over the aligned window. Equal horizontal spacing represents observations, not elapsed calendar time.</p></section><section class="metrics" aria-labelledby="metrics-title"><h2 id="metrics-title">Historical metrics</h2><p class="table-hint">Swipe the table to see every metric.</p><div class="table-scroll" role="region" aria-label="Historical metrics table" tabindex="0"><table><thead><tr><th>Series</th><th>Return</th><th>CAGR</th><th>Annualized volatility</th><th>Max drawdown</th></tr></thead><tbody>{rows}</tbody></table></div><details><summary>How to read these metrics</summary><dl><dt>Return</dt><dd>Change over this aligned window.</dd><dt>CAGR</dt><dd>The constant annual growth rate equivalent, using elapsed calendar days.</dd><dt>Annualized volatility</dt><dd>Variation in observation returns, scaled using the configured observation frequency.</dd><dt>Max drawdown</dt><dd>The largest decline from a previous peak in this window.</dd></dl><p>These describe the supplied history. They do not predict future returns.</p></details></section><section class="context" aria-label="Dataset context"><div><h2>Dataset provenance</h2><dl>{meta}</dl></div><div><h2>Interpretation limits</h2><ul>{warnings}</ul></div></section><section class="reproduction" aria-labelledby="reproduction-title"><h2 id="reproduction-title">Reproduction record</h2><pre tabindex="0" role="region" aria-label="Reproduction record JSON">{details}</pre><p>The report contains the source details, assumptions, aligned observations, and calculated results.</p></section></main></div></body></html>'''


def write_report(result, path, format, force=False):
    render = {
        "json": lambda r: json.dumps(r, indent=2, allow_nan=False) + "\n",
        "csv": csv_report,
        "html": html_report,
    }
    if format not in render:
        raise ValueError("Report format must be json, csv, or html.")
    # Finish rendering and writing before publishing the destination. A failed
    # render/write must never truncate an earlier report, even with --force.
    content = render[format](result)
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if force:
            os.replace(temporary, destination)
        else:
            # A same-directory hard link publishes atomically and refuses an
            # existing destination, including a competing writer's report.
            os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

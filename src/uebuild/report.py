"""JSON and HTML reporting for one or many BuildResults.

The HTML report is a single self-contained file (inline CSS, no network
dependencies) suitable for attaching to CI artifacts or emailing around.
"""
from __future__ import annotations

import datetime
import html
import json
from pathlib import Path
from typing import Dict, List, Sequence

from . import __version__, util
from .build import BuildResult


def summarize(results: Sequence[BuildResult]) -> Dict[str, object]:
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    return {
        "tool": "uebuild %s" % __version__,
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"
        ),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "errors": sum(r.error_count for r in results),
        "warnings": sum(r.warning_count for r in results),
        "durationSeconds": round(sum(r.duration_s for r in results), 2),
    }


def write_json(results: Sequence[BuildResult], path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summarize(results),
        "results": [r.to_dict() for r in results],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
       background: #0f1420; color: #dde4f0; }
header { padding: 28px 40px 12px; }
header h1 { margin: 0; font-size: 22px; letter-spacing: .5px; }
header h1 .accent { color: #4ea1ff; }
header .meta { color: #8b97ad; font-size: 13px; margin-top: 6px; }
.cards { display: flex; gap: 14px; padding: 18px 40px 6px; flex-wrap: wrap; }
.card { background: #182032; border: 1px solid #26314a; border-radius: 10px;
        padding: 14px 22px; min-width: 130px; }
.card .num { font-size: 26px; font-weight: 700; }
.card .lbl { color: #8b97ad; font-size: 12px; text-transform: uppercase;
             letter-spacing: 1px; }
.card.ok .num { color: #3fd68f; }
.card.bad .num { color: #ff5f6e; }
.card.warn .num { color: #ffcf5c; }
table { width: calc(100% - 80px); margin: 20px 40px 40px; border-collapse: collapse;
        background: #131a2a; border: 1px solid #26314a; border-radius: 10px;
        overflow: hidden; }
th, td { text-align: left; padding: 10px 14px; font-size: 14px;
         border-bottom: 1px solid #1e2740; vertical-align: top; }
th { background: #182032; color: #8b97ad; font-size: 12px;
     text-transform: uppercase; letter-spacing: 1px; }
tr:last-child td { border-bottom: none; }
.pill { display: inline-block; padding: 2px 12px; border-radius: 999px;
        font-size: 12px; font-weight: 700; }
.pill.pass { background: rgba(63,214,143,.15); color: #3fd68f; }
.pill.fail { background: rgba(255,95,110,.15); color: #ff5f6e; }
.chips span, .chips td { display: inline-block; }
.chip { display: inline-block; background: #1e2740; border-radius: 6px;
        padding: 1px 8px; margin: 1px 2px; font-size: 12px; color: #a9b8d6; }
.mono { font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
        font-size: 12px; word-break: break-all; color: #9fb3d9; }
details { margin-top: 6px; }
summary { cursor: pointer; color: #4ea1ff; font-size: 13px; }
details pre { background: #0b1020; border: 1px solid #26314a; border-radius: 8px;
              padding: 10px 12px; white-space: pre-wrap; word-break: break-word;
              max-height: 260px; overflow: auto; font-size: 12px; color: #e68a8a; }
details pre.warn { color: #d8bc72; }
a { color: #4ea1ff; }
.empty { padding: 60px 40px; color: #8b97ad; font-size: 15px; }
"""


def _pill(ok: bool) -> str:
    cls, text = ("pass", "PASS") if ok else ("fail", "FAIL")
    return '<span class="pill %s">%s</span>' % (cls, text)


def _chips(values) -> str:
    return '<span class="chips">%s</span>' % "".join(
        '<span class="chip">%s</span>' % html.escape(v) for v in values
    )


def _details(title: str, lines, warn: bool = False) -> str:
    if not lines:
        return ""
    body = "\n".join(html.escape(line) for line in lines)
    cls = ' class="warn"' if warn else ""
    return (
        "<details><summary>%s (%d)</summary><pre%s>%s</pre></details>"
        % (html.escape(title), len(lines), cls, body)
    )


def write_html(
    results: Sequence[BuildResult],
    path,
    title: str = "uebuild plugin build report",
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize(results)

    rows: List[str] = []
    for r in results:
        columns = [
            _pill(r.success),
            "<b>%s</b><div class='mono' style='color:#8b97ad'>%s</div>"
            % (html.escape(r.plugin_name), html.escape(r.label)),
            html.escape(r.engine_name),
            _chips(r.platforms),
            util.human_duration(r.duration_s),
            str(r.error_count),
            str(r.warning_count),
        ]
        last = (
            '<span class="mono">%s</span>%s%s%s'
            % (
                html.escape(r.message),
                "<br/>log: <span class='mono'>%s</span>"
                % html.escape(r.log_file or "n/a"),
                _details("command", [r.command]),
                _details("errors", r.errors) + _details("warnings", r.warnings, warn=True),
            )
        )
        columns.append(last)
        rows.append("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in columns))

    if not rows:
        body = '<div class="empty">No builds were run.</div>'
    else:
        body = (
            "<table><thead><tr>"
            "<th>Status</th><th>Plugin</th><th>Engine</th><th>Platforms</th>"
            "<th>Duration</th><th>Errors</th><th>Warnings</th><th>Details</th>"
            "</tr></thead><tbody>%s</tbody></table>" % "".join(rows)
        )

    duration = util.human_duration(float(summary["durationSeconds"]))
    page = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>%(title)s</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>%(css)s</style></head>
<body>
<header>
  <h1><span class="accent">ue</span>build &middot; %(title)s</h1>
  <div class="meta">Generated %(generated)s &middot; %(tool)s</div>
</header>
<section class="cards">
  <div class="card"><div class="num">%(total)d</div><div class="lbl">Builds</div></div>
  <div class="card ok"><div class="num">%(passed)d</div><div class="lbl">Passed</div></div>
  <div class="card bad"><div class="num">%(failed)d</div><div class="lbl">Failed</div></div>
  <div class="card warn"><div class="num">%(warnings)d</div><div class="lbl">Warnings</div></div>
  <div class="card"><div class="num">%(duration)s</div><div class="lbl">Total time</div></div>
</section>
%(body)s
</body></html>
""" % {
        "title": html.escape(title),
        "css": _CSS,
        "generated": html.escape(str(summary["generated"])),
        "tool": html.escape(str(summary["tool"])),
        "total": summary["total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "warnings": summary["warnings"],
        "duration": html.escape(duration),
        "body": body,
    }
    path.write_text(page, encoding="utf-8")
    return path

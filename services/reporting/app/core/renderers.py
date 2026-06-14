"""Output renderers — JSON, CSV, Markdown, HTML."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List, Optional


def render_json(data: Any) -> bytes:
    """Render ``data`` as pretty-printed JSON."""
    return json.dumps(data, indent=2, default=str).encode("utf-8")


def render_csv(records: List[Dict[str, Any]]) -> bytes:
    """Render records as CSV. Nested dicts are JSON-encoded."""
    if not records:
        return b""
    flat: List[Dict[str, Any]] = []
    for r in records:
        row: Dict[str, Any] = {}
        for k, v in r.items():
            if isinstance(v, (dict, list)):
                row[k] = json.dumps(v, default=str)
            else:
                row[k] = v
        flat.append(row)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(flat[0].keys()))
    writer.writeheader()
    for row in flat:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


_MARKDOWN_SKELETON = """# {title}

_Generated at: {ts}_

{body}
"""


def render_markdown(title: str, body: str) -> bytes:
    """Render a Markdown report from a title and body."""
    from shared.common.time import utcnow
    text = _MARKDOWN_SKELETON.format(title=title, ts=utcnow().isoformat(), body=body)
    return text.encode("utf-8")


_HTML_SKELETON = """<!DOCTYPE html>
<html lang=\"en\"><head>
<meta charset=\"utf-8\">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       max-width: 800px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
h1, h2, h3 {{ color: #1a365d; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
th {{ background: #f7fafc; }}
.meta {{ color: #888; font-size: 0.85em; }}
</style></head><body>
{body}
</body></html>
"""


def render_html(title: str, body_html: str) -> bytes:
    """Wrap a body in a minimal HTML shell."""
    return _HTML_SKELETON.format(title=title, body=body_html).encode("utf-8")


def render(format: str, data: Any, *, title: str = "Report", body: str = "") -> bytes:
    """Render ``data`` in the given format."""
    fmt = (format or "json").lower()
    if fmt == "json":
        return render_json(data)
    if fmt == "csv":
        records = data if isinstance(data, list) else [data]
        return render_csv(records)
    if fmt == "markdown" or fmt == "md":
        return render_markdown(title, body or json.dumps(data, indent=2, default=str))
    if fmt == "html":
        return render_html(title, body or f"<pre>{json.dumps(data, indent=2, default=str)}</pre>")
    raise ValueError(f"unsupported format: {format}")

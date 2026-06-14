"""Robust JSON extraction from LLM output.

Models occasionally emit prose around the JSON, or wrap it in ```json
fences. These helpers handle that gracefully.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def parse_json_output(text: str) -> Optional[Dict[str, Any]]:
    """Return the first JSON object embedded in ``text``, or None.

    Tries, in order:
      1. The whole string
      2. The first ```json ... ``` block
      3. The substring from the first ``{`` to the last ``}``
    """
    if not text:
        return None
    s = text.strip()
    # Direct parse
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Code fence
    m = _FENCE_RE.search(s)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Brace slice
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidate = s[first:last + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None


def extract_field(text: str, field: str) -> Optional[str]:
    """Regex fallback: extract ``"<field>": "<value>"`` from text."""
    pattern = rf'"{re.escape(field)}"\s*:\s*"([^"]+)"'
    m = re.search(pattern, text)
    if m:
        return m.group(1)
    pattern2 = rf'"{re.escape(field)}"\s*:\s*([^,\n}}]+)'
    m2 = re.search(pattern2, text)
    if m2:
        return m2.group(1).strip()
    return None

"""Template service — lookup + variable documentation."""

from __future__ import annotations

from typing import Any, Dict, List

from app.core.templating import TEMPLATES, list_templates


def get_template_info(name: str) -> Dict[str, Any] | None:
    """Return info for a single template, or None if unknown."""
    info = TEMPLATES.get(name)
    if info is None:
        return None
    return {
        "name": info.name,
        "description": info.description,
        "schedule": info.schedule,
        "required_data": info.required_data,
        "output_formats": info.output_formats,
    }


def list_all() -> List[Dict[str, Any]]:
    """Return info for all templates."""
    return list_templates()

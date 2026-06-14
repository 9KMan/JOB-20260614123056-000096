"""Tests for the AI Judgment parsers + cost calculator."""
import os
import sys

# Put the AI service on sys.path FIRST so its `app` package wins.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVICE_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "services", "ai_judgment"))
if _SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _SERVICE_ROOT)

from app.core.parsers import parse_json_output, extract_field
from app.core.cost import estimate_cost_usd, estimate_cost_cents


def test_parse_json_direct():
    assert parse_json_output('{"label": "x", "confidence": 0.9}') == {"label": "x", "confidence": 0.9}


def test_parse_json_with_fence():
    text = "Here's the JSON:\n```json\n{\"label\": \"y\"}\n```\nDone."
    assert parse_json_output(text) == {"label": "y"}


def test_parse_json_with_prose():
    text = 'Sure, here is the result: {"label": "z", "confidence": 0.5} -- hope this helps!'
    assert parse_json_output(text) == {"label": "z", "confidence": 0.5}


def test_parse_json_invalid_returns_none():
    assert parse_json_output("not json at all") is None


def test_parse_json_empty_returns_none():
    assert parse_json_output("") is None
    assert parse_json_output(None) is None


def test_extract_field_string():
    assert extract_field('{"label": "x", "confidence": 0.9}', "label") == "x"


def test_extract_field_object_fallback():
    val = extract_field('{"nested": {"k": "v"}}', "nested")
    assert "k" in (val or "")


def test_extract_field_missing():
    assert extract_field('{"label": "x"}', "missing") is None


def test_cost_gpt4o_mini_known():
    cost = estimate_cost_usd("gpt-4o-mini", 1000, 1000)
    assert abs(cost - 0.00075) < 1e-9


def test_cost_gpt4o_mini_with_version_suffix():
    cost = estimate_cost_usd("gpt-4o-mini-2024-07-18", 1000, 1000)
    assert abs(cost - 0.00075) < 1e-9


def test_cost_unknown_model_uses_fallback():
    cost = estimate_cost_usd("totally-unknown-model", 1000, 1000)
    assert abs(cost - 0.00075) < 1e-9


def test_cost_cents_conversion():
    cents = estimate_cost_cents("gpt-4o", 1_000_000, 500_000)
    assert abs(cents - 750.0) < 1e-6

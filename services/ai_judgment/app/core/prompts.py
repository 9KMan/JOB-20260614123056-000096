"""Prompt templates for each AITask family.

Each function returns ``(system, user)`` given the inputs. The system
prompt is the model's role + constraints; the user prompt is the
specific question or content to process.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from shared.contracts.ai_contract import AITask


# ----- Classify -----

def classify_prompt(*, content: str, labels: List[str], context: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    """Build the (system, user) pair for classification."""
    labels_csv = ", ".join(labels)
    ctx = ""
    if context:
        ctx = "\n\nContext:\n" + "\n".join(f"- {k}: {v}" for k, v in context.items())
    system = (
        "You are a classification assistant for an e-commerce / dropshipping platform. "
        "Read the content and decide which label best applies. "
        "Respond with JSON: {\"label\": <one of the allowed labels>, \"confidence\": <float 0..1>}"
    )
    user = (
        f"Allowed labels: {labels_csv}.\n"
        f"Allowed JSON shape: {{\"label\": str, \"confidence\": float}}.\n\n"
        f"Content:\n{content}{ctx}"
    )
    return system, user


# ----- Extract -----

def extract_prompt(*, content: str, fields: List[str], context: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    fields_csv = ", ".join(fields)
    ctx = ""
    if context:
        ctx = "\n\nContext:\n" + "\n".join(f"- {k}: {v}" for k, v in context.items())
    system = (
        "You are a structured-extraction assistant. "
        "Extract the requested fields from the content. "
        "Respond with JSON: {<field>: <value>, ...}."
    )
    user = f"Fields to extract: {fields_csv}.\n\nContent:\n{content}{ctx}"
    return system, user


# ----- Summarize -----

def summarize_prompt(*, content: str, max_words: int, context: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    ctx = ""
    if context:
        ctx = "\n\nContext:\n" + "\n".join(f"- {k}: {v}" for k, v in context.items())
    system = (
        "You are a summarization assistant. "
        "Produce a concise, neutral summary that captures the key facts. "
        f"Keep the summary under {max_words} words."
    )
    user = f"Content to summarize:\n{content}{ctx}"
    return system, user


# ----- Judge (free-form judgment) -----

def judge_prompt(
    *,
    content: str,
    schema_hint: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    ctx = ""
    if context:
        ctx = "\n\nContext:\n" + "\n".join(f"- {k}: {v}" for k, v in context.items())
    schema_block = ""
    if schema_hint:
        schema_block = "\nReturn JSON matching this shape:\n" + str(schema_hint)
    system = (
        "You are a judgment-call assistant for an e-commerce / dropshipping platform. "
        "Make a clear decision with a confidence score and a brief rationale. "
        "Always include a confidence field (0..1)." + schema_block
    )
    user = f"{content}{ctx}"
    return system, user


# ----- Draft (response generation) -----

def draft_prompt(
    *,
    content: str,
    persona: str = "polite, professional account manager",
    tone: str = "warm but direct",
    max_words: int = 180,
    context: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    ctx = ""
    if context:
        ctx = "\n\nContext:\n" + "\n".join(f"- {k}: {v}" for k, v in context.items())
    system = (
        f"You are drafting a response on behalf of a {persona}. "
        f"Tone: {tone}. Keep it under {max_words} words. "
        "Do not promise refunds, returns, or escalations without explicit approval."
    )
    user = f"Source content / context:\n{content}{ctx}"
    return system, user


# ----- Dispatch -----

def build_prompt(
    task: AITask,
    *,
    content: str,
    labels: Optional[List[str]] = None,
    fields: Optional[List[str]] = None,
    max_words: int = 120,
    schema_hint: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    persona: str = "polite, professional account manager",
    tone: str = "warm but direct",
) -> tuple[str, str]:
    """Build (system, user) for any AITask."""
    if task is AITask.CLASSIFY:
        return classify_prompt(content=content, labels=labels or [], context=context)
    if task is AITask.EXTRACT:
        return extract_prompt(content=content, fields=fields or [], context=context)
    if task is AITask.SUMMARIZE:
        return summarize_prompt(content=content, max_words=max_words, context=context)
    if task is AITask.JUDGE:
        return judge_prompt(content=content, schema_hint=schema_hint, context=context)
    if task is AITask.DRAFT:
        return draft_prompt(content=content, persona=persona, tone=tone, max_words=max_words, context=context)
    raise ValueError(f"unsupported task: {task}")

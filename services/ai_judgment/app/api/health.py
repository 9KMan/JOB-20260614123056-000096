"""Health endpoint."""

from fastapi import APIRouter

from app.adapters.factory import get_adapter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "ai-judgment",
        "version": "0.1.0",
    }


@router.get("/adapters")
async def list_adapters() -> dict:
    """List available adapters + their config status."""
    import os
    adapter = get_adapter()
    return {
        "active": adapter.name,
        "providers": {
            "openai": {"configured": bool(os.environ.get("OPENAI_API_KEY"))},
            "anthropic": {"configured": bool(os.environ.get("ANTHROPIC_API_KEY"))},
            "vllm": {
                "configured": bool(os.environ.get("VLLM_BASE_URL")),
                "status": "stub",
                "note": "Use OpenAIAdapter with OPENAI_BASE_URL until vllm_adapter.py is implemented",
            },
            "ollama": {
                "configured": bool(os.environ.get("OLLAMA_BASE_URL")),
                "status": "stub",
                "note": "Use OpenAIAdapter with OPENAI_BASE_URL until ollama_adapter.py is implemented",
            },
        },
    }

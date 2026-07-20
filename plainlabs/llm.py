"""Thin SLM runtime. One place to call the local model; skills build on this.

Design note: we keep temperature 0 and ask for tightly-scoped outputs, because a
2B model is reliable on narrow tasks and drifts on open ones. Skills that need a
structured answer parse + validate here and raise on failure so the graph can retry
or escalate — never silently accept malformed output.
"""
from functools import lru_cache

from langchain_ollama import ChatOllama

from plainlabs.config import SLM_MODEL, SLM_TEMPERATURE


@lru_cache(maxsize=1)
def _model() -> ChatOllama:
    return ChatOllama(model=SLM_MODEL, temperature=SLM_TEMPERATURE)


def ask(prompt: str) -> str:
    """One-shot SLM call, returns the raw text response (stripped)."""
    return _model().invoke(prompt).content.strip()

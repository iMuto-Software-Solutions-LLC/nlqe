"""Backwards-compatibility shim — moved to query_engine.llm.client."""

from query_engine.llm.client import LLMClient as OpenAIClient

__all__ = ["OpenAIClient"]

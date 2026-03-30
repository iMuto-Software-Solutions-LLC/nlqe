"""Backwards-compatibility shim — moved to nlqe.llm.client."""

from nlqe.llm.client import LLMClient as OpenAIClient

__all__ = ["OpenAIClient"]

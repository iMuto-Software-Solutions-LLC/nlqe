"""Backwards-compatibility shim — the OpenAI client has moved to query_engine.llm.

Import from ``query_engine.llm`` going forward::

    from query_engine.llm import LLMClient, openai_client
"""

from query_engine.llm.client import LLMClient as OpenAIClient

__all__ = ["OpenAIClient"]

"""Backwards-compatibility shim — the OpenAI client has moved to nlqe.llm.

Import from ``nlqe.llm`` going forward::

    from nlqe.llm import LLMClient, openai_client
"""

from nlqe.llm.client import LLMClient as OpenAIClient

__all__ = ["OpenAIClient"]

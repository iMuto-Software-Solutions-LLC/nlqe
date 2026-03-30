"""Unit tests for QueryEngineConfig."""

from __future__ import annotations

import pytest

from nlqe.config import QueryEngineConfig


class TestQueryEngineConfig:
    def test_defaults(self) -> None:
        cfg = QueryEngineConfig(openai_api_key="test-key")
        assert cfg.llm_provider == "openai"
        assert cfg.llm_model == "gpt-4o"
        assert cfg.llm_temperature == 0.0
        assert cfg.llm_max_tokens == 2000
        assert cfg.query_timeout_seconds == 30
        assert cfg.max_debug_attempts == 3
        assert cfg.log_level == "INFO"
        assert cfg.log_queries is True

    def test_openai_key_can_be_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Prevent .env file from injecting a real key
        monkeypatch.delenv("NLQE_OPENAI_API_KEY", raising=False)
        cfg = QueryEngineConfig(_env_file=None)  # type: ignore[call-arg]
        assert cfg.openai_api_key == ""

    def test_anthropic_key_defaults_empty(self) -> None:
        cfg = QueryEngineConfig()
        assert cfg.anthropic_api_key == ""

    def test_custom_values(self) -> None:
        cfg = QueryEngineConfig(
            llm_provider="anthropic",
            anthropic_api_key="sk-ant-xxx",
            llm_model="claude-3-5-sonnet-20241022",
            llm_temperature=0.5,
            max_debug_attempts=5,
            log_queries=False,
        )
        assert cfg.llm_provider == "anthropic"
        assert cfg.llm_model == "claude-3-5-sonnet-20241022"
        assert cfg.llm_temperature == 0.5
        assert cfg.max_debug_attempts == 5
        assert cfg.log_queries is False

    def test_few_shot_path_defaults_none(self) -> None:
        cfg = QueryEngineConfig()
        assert cfg.few_shot_examples_path is None

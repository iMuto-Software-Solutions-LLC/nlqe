"""Multi-turn conversation management backed by LangChain message history."""

from typing import Any

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

from nlqe.query.loop import QueryLoop
from nlqe.types import (
    ConversationResponse,
    ConversationTurn,
)  # ConversationTurn used in get_history()
from nlqe.utils import get_logger

logger = get_logger(__name__)


class ConversationManager:
    """Manage multi-turn conversations using LangChain message history.

    History is stored as ``HumanMessage`` / ``AIMessage`` pairs and
    serialised into the schema context string that is prepended to every
    subsequent query.  The window size (default 6 messages = 3 turns)
    keeps prompt length bounded.
    """

    def __init__(
        self,
        query_loop: QueryLoop,
        context: str,
        history: BaseChatMessageHistory | None = None,
        window_size: int = 6,
    ) -> None:
        """Initialise.

        Args:
            query_loop: ``QueryLoop`` instance for executing queries.
            context: Static datasource schema context (markdown).
            history: LangChain message history backend.  Defaults to an
                in-memory ``ChatMessageHistory``.
            window_size: Maximum number of *messages* (not turns) to include
                from history.  Defaults to 6 (= last 3 turns).
        """
        self.query_loop = query_loop
        self.base_context = context
        self.history: BaseChatMessageHistory = history or ChatMessageHistory()
        self.window_size = window_size
        self.turn_number = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(self, user_input: str) -> ConversationResponse:
        """Ask a question in the ongoing conversation.

        Args:
            user_input: Natural language question from the user.

        Returns:
            ``ConversationResponse`` enriched with turn metadata.

        Raises:
            DebugFailedError: If the underlying query fails after all attempts.
        """
        self.turn_number += 1
        logger.info(f"Conversation turn {self.turn_number}: {user_input!r}")

        # Inject conversation history into schema context
        context_with_history = self._build_context_with_history()

        # Run the query pipeline
        response = self.query_loop.execute(user_input, context_with_history)

        # Persist turn to message history
        self.history.add_message(HumanMessage(content=user_input))
        self.history.add_message(AIMessage(content=response.answer))

        return ConversationResponse(
            user_query=response.user_query,
            generated_sql=response.generated_sql,
            data=response.data,
            answer=response.answer,
            confidence_score=response.confidence_score,
            execution_time_ms=response.execution_time_ms,
            result_rows=response.result_rows,
            debug_info=response.debug_info,
            error=response.error,
            turn_number=self.turn_number,
            expanded_query=user_input,
            context_used=context_with_history,
            previous_results_referenced=False,
        )

    def get_history(self) -> list[ConversationTurn]:
        """Return typed history as a list of ``ConversationTurn`` objects.

        Note: rebuilds from the raw message history so it is always consistent
        with the underlying store.
        """
        turns: list[ConversationTurn] = []
        messages = self.history.messages
        # Messages are interleaved Human/AI pairs
        for i in range(0, len(messages) - 1, 2):
            human = messages[i]
            ai = messages[i + 1]
            turns.append(
                ConversationTurn(
                    turn_number=i // 2 + 1,
                    user_input=str(human.content),
                    expanded_query=str(human.content),
                    generated_sql="",  # not stored in history messages
                    results_summary="",
                    answer=str(ai.content),
                    execution_time_ms=0.0,
                )
            )
        return turns

    def get_context(self) -> str:
        """Return the full context that would be passed on the next query."""
        return self._build_context_with_history()

    def clear(self) -> None:
        """Clear all conversation history and reset turn counter."""
        self.history.clear()
        self.turn_number = 0
        logger.info("Conversation cleared")

    def get_last_results(self) -> list[dict[str, Any]] | None:
        """Results from the most recent query (not available from history alone)."""
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_context_with_history(self) -> str:
        """Append a sliding window of conversation history to the schema context."""
        messages = self.history.messages[-self.window_size :]
        if not messages:
            return self.base_context

        history_lines = ["\n\nConversation History:"]
        turn_idx = 1
        for i in range(0, len(messages) - 1, 2):
            human = messages[i]
            ai = messages[i + 1] if i + 1 < len(messages) else None
            history_lines.append(f"Turn {turn_idx}: {human.content}")
            if ai:
                history_lines.append(f"Answer: {ai.content}")
            turn_idx += 1

        return self.base_context + "\n".join(history_lines)

    @staticmethod
    def _summarize_results(results: list[dict[str, Any]]) -> str:
        if not results:
            return "No results"
        if len(results) == 1:
            return f"1 result: {results[0]}"
        return f"{len(results)} results (first: {results[0]})"

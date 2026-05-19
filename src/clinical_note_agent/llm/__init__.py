"""LLM 客户端抽象（OpenAI-compatible）。"""

from clinical_note_agent.llm.client import LlmClient, LlmMessage
from clinical_note_agent.llm.mock import MockLlmClient
from clinical_note_agent.llm.openai_compatible import OpenAICompatibleClient

__all__ = [
    "LlmClient",
    "LlmMessage",
    "MockLlmClient",
    "OpenAICompatibleClient",
]

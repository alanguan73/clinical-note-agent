from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LlmMessage:
    role: str
    content: str


class LlmClient(Protocol):
    """OpenAI-compatible chat 抽象。"""

    def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float = 0,
        response_format_json: bool = True,
    ) -> str: ...

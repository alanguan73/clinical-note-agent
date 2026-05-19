from __future__ import annotations

import json
from typing import Callable

from clinical_note_agent.llm.client import LlmMessage


class MockLlmClient:
    """测试用 LLM：按调用次序或关键词返回固定 JSON。"""

    def __init__(
        self,
        responses: list[str] | None = None,
        handler: Callable[[list[LlmMessage]], str] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._handler = handler
        self.calls: list[list[LlmMessage]] = []

    def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float = 0,
        response_format_json: bool = True,
    ) -> str:
        self.calls.append(list(messages))
        if self._handler:
            return self._handler(messages)
        if not self._responses:
            raise RuntimeError("MockLlmClient 无可用响应")
        return self._responses.pop(0)

    @staticmethod
    def json_response(data: dict) -> str:
        return json.dumps(data, ensure_ascii=False)

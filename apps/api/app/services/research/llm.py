"""Groq adapter for the research orchestrator.

The orchestrator (`agents.py`) is written once against a single call shape:
`await client.messages.create(model=, max_tokens=, system=, tools=, messages=)`
returning an object with `.content` (blocks with `.type`/`.text`/`.id`/`.name`/
`.input`), `.stop_reason`, and `.usage.input_tokens`/`.output_tokens` — exactly
the shape of an Anthropic SDK response. Anthropic's own client already matches
this, so it's passed to the orchestrator unmodified. `GroqResearchClient`
below translates that same call shape to and from Groq's OpenAI-compatible
chat completions API, so the orchestrator needs no provider-specific branches.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class NormalizedBlock:
    type: str  # "text" | "tool_use"
    text: str | None = None
    id: str | None = None
    name: str | None = None
    input: dict[str, Any] | None = None


@dataclass
class NormalizedUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class NormalizedResponse:
    content: list[NormalizedBlock]
    stop_reason: str
    usage: NormalizedUsage


class _GroqMessages:
    def __init__(self, client: Any) -> None:
        self._client = client

    async def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]],
    ) -> NormalizedResponse:
        openai_messages: list[dict[str, Any]] = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        for msg in messages:
            openai_messages.extend(self._translate_message(msg))

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = [self._to_openai_tool(t) for t in tools]
            kwargs["tool_choice"] = "auto"

        response = await self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        blocks: list[NormalizedBlock] = []
        if message.content:
            blocks.append(NormalizedBlock(type="text", text=message.content))

        tool_calls = getattr(message, "tool_calls", None) or []
        for call in tool_calls:
            try:
                parsed_input = json.loads(call.function.arguments) if call.function.arguments else {}
            except json.JSONDecodeError:
                parsed_input = {}
            blocks.append(
                NormalizedBlock(type="tool_use", id=call.id, name=call.function.name, input=parsed_input)
            )

        usage = response.usage
        return NormalizedResponse(
            content=blocks,
            stop_reason="tool_use" if tool_calls else "end_turn",
            usage=NormalizedUsage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
        )

    @staticmethod
    def _to_openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }

    @staticmethod
    def _translate_message(msg: dict[str, Any]) -> list[dict[str, Any]]:
        """Translate one Anthropic-shaped history entry to 0+ OpenAI-shaped ones.

        Only shapes actually produced by `agents.run_agent` need handling:
        a plain-string user message, an assistant message whose `content` is
        a list of `NormalizedBlock` (this adapter's own prior output), or a
        user message whose `content` is a list of plain `tool_result` dicts.
        """
        role = msg["role"]
        content = msg["content"]

        if isinstance(content, str):
            return [{"role": role, "content": content}]

        if role == "assistant":
            text_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            for block in content:
                if block.type == "text" and block.text:
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input or {}),
                            },
                        }
                    )
            entry: dict[str, Any] = {"role": "assistant", "content": "\n".join(text_parts) or None}
            if tool_calls:
                entry["tool_calls"] = tool_calls
            return [entry]

        # role == "user": a list of tool_result dicts appended by run_agent.
        tool_messages: list[dict[str, Any]] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                tool_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": block["tool_use_id"],
                        "content": block["content"],
                    }
                )
        return tool_messages


class GroqResearchClient:
    """Duck-types `anthropic.AsyncAnthropic`'s `.messages.create(...)` surface
    on top of Groq's OpenAI-compatible API, so the research orchestrator can
    use either provider interchangeably.
    """

    def __init__(self, api_key: str) -> None:
        from groq import AsyncGroq  # lazy: keep the import off the hot path

        self.messages = _GroqMessages(AsyncGroq(api_key=api_key))

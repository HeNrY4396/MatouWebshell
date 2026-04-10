from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from typing import Iterable

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


@dataclass(slots=True)
class CodexProxyConfig:
    api_key: str
    base_url: str
    model_name: str
    temperature: float = 0.1
    timeout: float = 120.0


def _message_content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)

    return str(content)


class CodexProxyClient:
    def __init__(self, config: CodexProxyConfig) -> None:
        self.config = config
        self.endpoint = f"{config.base_url.rstrip('/')}/chat/completions"

    def _stream_chat(self, headers: dict[str, str], payload: dict) -> str:
        """
        流式请求（stream=True），逐行读取 SSE 数据块并手动拼接 content。
        优先 HTTP/2，失败则回退 HTTP/1.1。
        """
        timeout = httpx.Timeout(self.config.timeout)
        last_error: BaseException | None = None

        for use_http2 in (True, False):
            try:
                with httpx.Client(http2=use_http2, timeout=timeout) as client:
                    with client.stream(
                        "POST",
                        self.endpoint,
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code >= 400:
                            response.read()
                            raise RuntimeError(
                                f"Codex proxy request failed with status "
                                f"{response.status_code}: {response.text}"
                            )

                        chunks: list[str] = []
                        for line in response.iter_lines():
                            line = line.strip()
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices") or []
                                if choices:
                                    delta = choices[0].get("delta") or {}
                                    piece = delta.get("content")
                                    if piece:
                                        chunks.append(piece)
                            except json.JSONDecodeError:
                                continue

                        return "".join(chunks)

            except ImportError:
                # 未安装 h2 时 httpx 禁止 http2=True，直接尝试下一轮 HTTP/1.1
                last_error = None
                continue
            except (httpx.HTTPError, OSError, ssl.SSLError) as exc:
                last_error = exc
                if use_http2:
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("Codex proxy request failed: unable to establish HTTP client.")

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        payload = {
            "model": self.config.model_name,
            "temperature": self.config.temperature,
            "stream": True,
            "messages": self._convert_messages(messages),
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "eternity-agent/0.1",
        }

        content = self._stream_chat(headers, payload)

        if not content.strip():
            raise RuntimeError("Codex proxy returned no assistant message content from stream.")

        return AIMessage(content=content.strip())

    def _convert_messages(self, messages: Iterable[BaseMessage]) -> list[dict[str, str]]:
        converted: list[dict[str, str]] = []

        for message in messages:
            role = "user"
            if isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"

            converted.append(
                {
                    "role": role,
                    "content": _message_content_to_text(message.content),
                }
            )

        return converted

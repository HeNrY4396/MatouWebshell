from __future__ import annotations

import json
import ssl
from dataclasses import dataclass

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


@dataclass(slots=True)
class GeminiProxyConfig:
    api_key: str
    base_url: str
    model_name: str
    temperature: float = 0.1
    timeout: float = 120.0


class GeminiProxyClient:
    """
    适配 Google Gemini 原生 API 格式的 LLM 客户端。

    请求格式（区别于 OpenAI 格式）：
    - URL:  {base_url}/v1beta/models/{model_name}:generateContent
    - 系统提示词放在顶层 systemInstruction 字段，不进入 contents
    - contents 使用 role: "user" / "model"，对应 HumanMessage / AIMessage
    - 温度放在 generationConfig.temperature

    响应格式：
    - candidates[0].content.parts[].text
    """

    def __init__(self, config: GeminiProxyConfig) -> None:
        self.config = config
        self.endpoint = (
            f"{config.base_url.rstrip('/')}/v1beta/models/{config.model_name}:generateContent"
        )

    def _post_chat(self, headers: dict[str, str], payload: dict) -> httpx.Response:
        """优先 HTTP/2；失败则回退 HTTP/1.1。"""
        timeout = httpx.Timeout(self.config.timeout)
        last_error: BaseException | None = None

        for use_http2 in (True, False):
            try:
                with httpx.Client(http2=use_http2, timeout=timeout) as client:
                    return client.post(
                        self.endpoint,
                        headers=headers,
                        json=payload,
                    )
            except ImportError:
                last_error = None
                continue
            except (httpx.HTTPError, OSError, ssl.SSLError) as exc:
                last_error = exc
                if use_http2:
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("Gemini proxy request failed: unable to establish HTTP client.")

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        system_instruction, contents = self._convert_messages(messages)

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.config.temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        response = self._post_chat(headers, payload)

        if response.status_code >= 400:
            raise RuntimeError(
                f"Gemini proxy request failed with status {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Gemini proxy returned invalid JSON: {response.text}"
            ) from exc

        api_error = data.get("error")
        if api_error:
            raise RuntimeError(f"Gemini proxy error: {api_error}")

        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise RuntimeError(
                "Gemini proxy returned no candidates. "
                f"Response: {json.dumps(data, ensure_ascii=False)}"
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if text.strip():
            return AIMessage(content=text.strip())

        raise RuntimeError(
            "Gemini proxy returned no text content. "
            f"Response: {json.dumps(data, ensure_ascii=False)}"
        )

    def _convert_messages(
        self, messages: list[BaseMessage]
    ) -> tuple[str, list[dict]]:
        """
        将 LangChain 消息列表转换为 Gemini API 格式：
        - SystemMessage → 顶层 systemInstruction 字符串（不进 contents）
        - HumanMessage → role: "user"
        - AIMessage    → role: "model"

        Gemini 额外约束：
        - contents 必须以 "user" 开头
        - 相邻同 role 的消息需合并（不允许连续两条相同 role）
        """
        system_instruction = ""
        raw: list[tuple[str, str]] = []

        for message in messages:
            text = self._message_to_text(message)
            if isinstance(message, SystemMessage):
                system_instruction = (
                    (system_instruction + "\n\n" + text).strip()
                    if system_instruction
                    else text
                )
            elif isinstance(message, HumanMessage):
                raw.append(("user", text))
            elif isinstance(message, AIMessage):
                raw.append(("model", text))

        # 合并相邻同 role 的消息
        merged: list[list[str, str]] = []
        for role, text in raw:
            if merged and merged[-1][0] == role:
                merged[-1][1] = merged[-1][1] + "\n\n" + text
            else:
                merged.append([role, text])

        # Gemini 要求 contents 第一条必须是 user
        while merged and merged[0][0] == "model":
            merged.pop(0)

        contents = [
            {"role": role, "parts": [{"text": text}]}
            for role, text in merged
        ]
        return system_instruction, contents

    @staticmethod
    def _message_to_text(message: BaseMessage) -> str:
        content = message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                else:
                    parts.append(str(item))
            return "\n".join(p for p in parts if p)
        return str(content)

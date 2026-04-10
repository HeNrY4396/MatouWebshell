from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from .codex_proxy_client import CodexProxyClient, CodexProxyConfig
from .gemini_proxy_client import GeminiProxyClient, GeminiProxyConfig


class PayloadAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    generated_code: str
    compile_success: bool
    compile_message: str
    compile_attempts: int


@dataclass(slots=True)
class PayloadAgentConfig:
    api_key: str
    model_name: str
    base_url: str | None = None
    provider: Literal["openai", "codex_proxy", "gemini_proxy"] = "openai"
    temperature: float = 0.1
    max_compile_attempts: int = 3


def message_text(message: BaseMessage) -> str:
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
        return "\n".join(part for part in parts if part)
    return str(content)


def last_ai_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message_text(message)
    return ""


class BasePayloadAgent:
    prompt_root = Path(__file__).resolve().parent / "prompts"
    prompt_relative_path = ""
    output_language = "text"

    def __init__(self, config: PayloadAgentConfig) -> None:
        self.config = config
        self.llm = self._create_llm_client()
        self.graph = self._build_graph()

    def _create_llm_client(self):
        if self.config.provider == "openai":
            return ChatOpenAI(
                model=self.config.model_name,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                temperature=self.config.temperature,
            )

        if self.config.provider == "codex_proxy":
            if not self.config.base_url:
                raise ValueError(
                    "PayloadAgentConfig.base_url is required for codex_proxy provider."
                )
            return CodexProxyClient(
                CodexProxyConfig(
                    model_name=self.config.model_name,
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    temperature=self.config.temperature,
                )
            )

        if self.config.provider == "gemini_proxy":
            if not self.config.base_url:
                raise ValueError(
                    "PayloadAgentConfig.base_url is required for gemini_proxy provider."
                )
            return GeminiProxyClient(
                GeminiProxyConfig(
                    model_name=self.config.model_name,
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    temperature=self.config.temperature,
                )
            )

        raise ValueError(f"Unsupported provider: {self.config.provider}")

    def _read_prompt(self) -> str:
        prompt_path = self.prompt_root / self.prompt_relative_path
        return prompt_path.read_text(encoding="utf-8").strip()

    def _build_system_prompt(self) -> str:
        return self._read_prompt()

    def _build_graph(self):
        graph = StateGraph(PayloadAgentState)
        graph.add_node("generate", self._generate_node)
        graph.add_node("compile", self._compile_node)
        graph.add_edge(START, "generate")
        graph.add_edge("generate", "compile")
        graph.add_conditional_edges(
            "compile",
            self._is_compile_success,
            {
                "retry": "generate",
                "end": END,
            },
        )
        return graph.compile()

    def _generate_node(self, state: PayloadAgentState) -> PayloadAgentState:
        response = self.llm.invoke(
            [SystemMessage(content=self._build_system_prompt()), *state["messages"]]
        )
        response_text = message_text(response)
        return {
            "messages": [response],
            "generated_code": self.extract_generated_code(response_text),
        }

    def _compile_node(self, state: PayloadAgentState) -> PayloadAgentState:
        compile_attempts = state.get("compile_attempts", 0) + 1
        generated_code = state.get("generated_code", "").strip()

        if not generated_code:
            compile_message = self.get_missing_code_feedback()
            return {
                "compile_attempts": compile_attempts,
                "compile_success": False,
                "compile_message": compile_message,
                "messages": [HumanMessage(content=compile_message)],
            }

        success, compile_message = self.validate_generated_code(generated_code)
        updates: PayloadAgentState = {
            "compile_attempts": compile_attempts,
            "compile_success": success,
            "compile_message": compile_message,
        }

        if not success:
            updates["messages"] = [
                HumanMessage(content=self.get_validation_failure_feedback(compile_message))
            ]

        return updates

    def _is_compile_success(self, state: PayloadAgentState) -> str:
        if state.get("compile_success"):
            return "end"
        if state.get("compile_attempts", 0) >= self.config.max_compile_attempts:
            return "end"
        return "retry"

    def get_missing_code_feedback(self) -> str:
        return (
            "The previous response did not contain a valid source code block.\n"
            f"{self.get_required_output_instructions()}"
        )

    def get_validation_failure_feedback(self, validation_message: str) -> str:
        return (
            "The generated source code failed validation.\n"
            f"{validation_message}\n"
            f"Fix the code and return the output again.\n"
            f"{self.get_required_output_instructions()}"
        )

    def get_required_output_instructions(self) -> str:
        return (
            f"Return one complete {self.output_language} file inside a single "
            f"```{self.output_language}``` block."
        )

    def extract_generated_code(self, content: str) -> str:
        block_pattern = re.compile(
            rf"```{re.escape(self.output_language)}\s*(.*?)```",
            re.IGNORECASE | re.DOTALL,
        )
        match = block_pattern.search(content)
        if match:
            return match.group(1).strip()
        return content.strip()

    def validate_generated_code(self, source_code: str) -> tuple[bool, str]:
        raise NotImplementedError

    def extract_result_metadata(
        self,
        raw_response: str,
        generated_code: str,
    ) -> dict[str, object]:
        return {}

    def run(self, requirement: str) -> dict[str, object]:
        final_state = self.graph.invoke(
            {
                "messages": [HumanMessage(content=requirement)],
                "generated_code": "",
                "compile_success": False,
                "compile_message": "",
                "compile_attempts": 0,
            }
        )

        raw_response = last_ai_text(final_state.get("messages", []))
        generated_code = final_state.get("generated_code", "")
        result = {
            "requirement": requirement,
            "compile_success": final_state.get("compile_success", False),
            "compile_message": final_state.get("compile_message", ""),
            "compile_attempts": final_state.get("compile_attempts", 0),
            "generated_code": generated_code,
            "raw_response": raw_response,
        }
        result.update(self.extract_result_metadata(raw_response, generated_code))

        return result

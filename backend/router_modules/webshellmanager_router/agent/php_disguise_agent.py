from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from .base_payload_agent import BasePayloadAgent, PayloadAgentConfig, PayloadAgentState, message_text


PHP_BLOCK_RE = re.compile(r"```php\s*(.*?)```", re.IGNORECASE | re.DOTALL)
JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.IGNORECASE | re.DOTALL)

DISGUISE_SAMPLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "webshell"
    / "php"
    / "normal_template"
    / "DbConfigLoader..php"
)


def extract_php_disguise_code(content: str) -> str:
    match = PHP_BLOCK_RE.search(content)
    if match:
        return match.group(1).strip()
    return content.strip()


def extract_json_block(content: str) -> dict[str, object]:
    match = JSON_BLOCK_RE.search(content)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1).strip())
    except Exception:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def sanitize_php_filename(filename: str) -> str:
    raw_name = (filename or "").strip()
    if raw_name.lower().endswith(".php"):
        raw_name = raw_name[:-4]
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "", raw_name)
    if not cleaned:
        cleaned = "BusinessFacade"
    return f"{cleaned}.php"


class PhpDisguiseAgent(BasePayloadAgent):
    prompt_relative_path = "php/php_disguise_system.md"
    output_language = "php"

    def __init__(
        self,
        config: PayloadAgentConfig,
        disguise_sample_path: Path | None = None,
    ) -> None:
        self.disguise_sample_path = disguise_sample_path or DISGUISE_SAMPLE_PATH
        self.disguise_sample_source = self.disguise_sample_path.read_text(encoding="utf-8")
        super().__init__(config)

    def _build_graph(self):
        graph = StateGraph(PayloadAgentState)
        graph.add_node("generate", self._generate_node)
        graph.add_node("compile", self._compile_node)
        graph.add_edge(START, "generate")
        # 若 AI 响应中没有 php 代码块（如被安全机制拒绝），直接终止，不走 compile
        graph.add_conditional_edges(
            "generate",
            self._is_valid_code,
            {"compile": "compile", "abort": END},
        )
        graph.add_conditional_edges(
            "compile",
            self._is_compile_success,
            {"retry": "generate", "end": END},
        )
        return graph.compile()

    def _is_valid_code(self, state: PayloadAgentState) -> str:
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                if PHP_BLOCK_RE.search(message_text(msg)):
                    return "compile"
                # AI 响应中没有 php 代码块，判定为拒绝，中断流程
                return "abort"
        return "compile"

    def _build_system_prompt(self) -> str:
        prompt_template = self._read_prompt()
        return prompt_template.format(
            disguise_sample_source=self.disguise_sample_source,
        )

    def extract_generated_code(self, content: str) -> str:
        return extract_php_disguise_code(content)

    def get_required_output_instructions(self) -> str:
        return (
            "Return two code blocks in this order:\n"
            "1. One complete PHP file inside a single ```php``` block.\n"
            '2. One valid JSON object inside a single ```json``` block with this shape:\n'
            '{"php_filename":"BusinessFacade.php"}'
        )

    def validate_generated_code(self, source_code: str) -> tuple[bool, str]:
        required_fragments: dict[str, bool] = {
            "cookie_name placeholder": "$cookie_name$" in source_code,
            "secret_key placeholder": "$secret_key$" in source_code,
            "payload placeholder": "$payload$" in source_code,
            "cookie access control": "$_COOKIE[" in source_code,
            "base64_decode call": "base64_decode(" in source_code,
            "XOR decrypt": "^" in source_code,
            "eval or include execution": ("eval(" in source_code or "@include(" in source_code),
            "class definition": re.search(r"\bclass\s+\w+", source_code) is not None,
        }
        missing = [label for label, ok in required_fragments.items() if not ok]
        if missing:
            return False, "Missing required PHP disguise features: " + ", ".join(missing)

        if not source_code.strip().startswith("<?php"):
            return False, "PHP file must start with <?php."

        return True, "PHP disguise validation passed."

    def extract_result_metadata(
        self,
        raw_response: str,
        generated_code: str,
    ) -> dict[str, object]:
        metadata = extract_json_block(raw_response)
        php_filename = metadata.get("php_filename")
        if not isinstance(php_filename, str) or not php_filename.strip():
            # Infer a conservative filename when the model omits metadata.
            class_match = re.search(r"class\s+([A-Za-z][A-Za-z0-9_]*)", generated_code)
            if class_match:
                php_filename = class_match.group(1)
            else:
                php_filename = "BusinessFacade"

        return {
            "php_filename": sanitize_php_filename(php_filename),
        }

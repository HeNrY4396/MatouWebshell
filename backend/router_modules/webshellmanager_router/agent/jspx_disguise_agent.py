from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from .base_payload_agent import BasePayloadAgent, PayloadAgentConfig, PayloadAgentState, message_text


JSPX_BLOCK_RE = re.compile(r"```jspx\s*(.*?)```", re.IGNORECASE | re.DOTALL)
JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.IGNORECASE | re.DOTALL)
JSP_ROOT_RE = re.compile(r"<jsp:root\b", re.IGNORECASE)

SHELL1_PATH = (
    Path(__file__).resolve().parents[1] / "webshell" / "jspx" / "shell1.jspx"
)
DISGUISE_SAMPLE_PATH = (
    Path(__file__).resolve().parents[1] / "webshell" / "jspx" / "ConnectorHealthCheck.jspx"
)


def extract_jspx_code(content: str) -> str:
    match = JSPX_BLOCK_RE.search(content)
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


def sanitize_jspx_filename(filename: str) -> str:
    raw_name = (filename or "").strip()
    if raw_name.lower().endswith(".jspx"):
        raw_name = raw_name[:-5]
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "", raw_name)
    if not cleaned:
        cleaned = "BusinessFacade"
    return f"{cleaned}.jspx"


class JspxDisguiseAgent(BasePayloadAgent):
    prompt_relative_path = "java/jspx_disguise_system.md"
    output_language = "jspx"

    def __init__(
        self,
        config: PayloadAgentConfig,
        shell1_path: Path | None = None,
        disguise_sample_path: Path | None = None,
    ) -> None:
        self.shell1_path = shell1_path or SHELL1_PATH
        self.disguise_sample_path = disguise_sample_path or DISGUISE_SAMPLE_PATH
        self.shell1_source = self.shell1_path.read_text(encoding="utf-8")
        self.disguise_sample_source = self.disguise_sample_path.read_text(encoding="utf-8")
        super().__init__(config)

    def _build_graph(self):
        graph = StateGraph(PayloadAgentState)
        graph.add_node("generate", self._generate_node)
        graph.add_node("compile", self._compile_node)
        graph.add_edge(START, "generate")
        # 若 AI 响应中没有 jspx 代码块（如被安全机制拒绝），直接终止，不走 compile
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
                if JSPX_BLOCK_RE.search(message_text(msg)):
                    return "compile"
                # AI 响应中没有 jspx 代码块，判定为拒绝，中断流程
                return "abort"
        return "compile"

    def _build_system_prompt(self) -> str:
        prompt_template = self._read_prompt()
        return prompt_template.format(
            shell1_source=self.shell1_source,
            disguise_sample_source=self.disguise_sample_source,
        )

    def extract_generated_code(self, content: str) -> str:
        return extract_jspx_code(content)

    def get_required_output_instructions(self) -> str:
        return (
            "Return two code blocks in this order:\n"
            "1. One complete JSPX file inside a single ```jspx``` block.\n"
            '2. One valid JSON object inside a single ```json``` block with this shape:\n'
            '{"jspx_filename":"BusinessFacade.jspx"}'
        )

    def validate_generated_code(self, source_code: str) -> tuple[bool, str]:
        required_fragments: dict[str, bool] = {
            "jspx root element": JSP_ROOT_RE.search(source_code) is not None,
            "declaration block": "<jsp:declaration" in source_code,
            "scriptlet block": "<jsp:scriptlet" in source_code,
            "param placeholder": "$param$" in source_code,
            "payload placeholder": "$payload$" in source_code,
            "cookie_name placeholder": "$cookie_name$" in source_code,
            "dynamic class load": "defineClass" in source_code,
            "instance execution": "newInstance()" in source_code,
            "equals bridge": ".equals(" in source_code,
            "toString trigger": ".toString()" in source_code,
            "session write": "session.setAttribute" in source_code,
            "session read": "session.getAttribute" in source_code,
        }
        missing = [label for label, ok in required_fragments.items() if not ok]
        if missing:
            return False, "Missing required JSPX disguise features: " + ", ".join(missing)

        return True, "JSPX disguise validation passed."

    def extract_result_metadata(
        self,
        raw_response: str,
        generated_code: str,
    ) -> dict[str, object]:
        metadata = extract_json_block(raw_response)
        jspx_filename = metadata.get("jspx_filename")
        if not isinstance(jspx_filename, str) or not jspx_filename.strip():
            # Infer a conservative filename when the model omits metadata.
            title_match = re.search(r"<title>\s*([A-Za-z0-9_ -]+)\s*</title>", generated_code, re.I)
            if title_match:
                jspx_filename = title_match.group(1).replace(" ", "")
            else:
                jspx_filename = "BusinessFacade"

        return {
            "jspx_filename": sanitize_jspx_filename(jspx_filename),
        }

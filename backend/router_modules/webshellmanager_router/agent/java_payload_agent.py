from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from .base_payload_agent import BasePayloadAgent, PayloadAgentConfig
from ..java.javaPayload import javaPayload


JAVA_BLOCK_RE = re.compile(r"```java\s*(.*?)```", re.IGNORECASE | re.DOTALL)
JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.IGNORECASE | re.DOTALL)
PUBLIC_CLASS_RE = re.compile(r"public\s+class\s+([A-Za-z_][A-Za-z0-9_]*)")
METHOD_NAME_RE = re.compile(r'methodName\.equals\("([^"]+)"\)|"([^"]+)"\.equals\(methodName\)')
GET_PARAM_RE = re.compile(r'(?:this\.)?get\("([^"]+)"\)')
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1] / "java" / "payload" / "PayloadTemplate.java"
)


def extract_java_code(content: str) -> str:
    match = JAVA_BLOCK_RE.search(content)
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


def infer_method_name(source_code: str) -> str:
    for match in METHOD_NAME_RE.finditer(source_code):
        method_name = match.group(1) or match.group(2) or ""
        if method_name:
            return method_name
    return ""


def _guess_example_value(param_name: str):
    lower_name = param_name.lower()
    if lower_name in {"ip", "host", "targetip", "remoteip"}:
        return "192.168.47.123"
    if "port" in lower_name:
        return 3389
    if "path" in lower_name or "dir" in lower_name:
        return "/tmp/test.txt"
    if "file" in lower_name and "name" in lower_name:
        return "test.txt"
    if "content" in lower_name or "text" in lower_name:
        return "hello world"
    if "cmd" in lower_name or "command" in lower_name:
        return "whoami"
    if "url" in lower_name:
        return "http://127.0.0.1/test"
    if lower_name.startswith("is") or lower_name.startswith("enable"):
        return True
    return ""


def infer_param_example(source_code: str) -> dict[str, object]:
    param_names: list[str] = []
    for match in GET_PARAM_RE.finditer(source_code):
        param_name = match.group(1)
        if not param_name or param_name == "methodName":
            continue
        if param_name not in param_names:
            param_names.append(param_name)
    return {name: _guess_example_value(name) for name in param_names}


class JavaPayloadAgent(BasePayloadAgent):
    prompt_relative_path = "java/payload_system.md"
    output_language = "java"

    def __init__(
        self,
        config: PayloadAgentConfig,
        template_path: Path | None = None,
    ) -> None:
        self.template_path = template_path or TEMPLATE_PATH
        self.template_source = self.template_path.read_text(encoding="utf-8")
        self.compiler = javaPayload()
        super().__init__(config)

    def _build_system_prompt(self) -> str:
        prompt_template = self._read_prompt()
        return prompt_template.format(template_source=self.template_source)

    def extract_generated_code(self, content: str) -> str:
        return extract_java_code(content)

    def get_required_output_instructions(self) -> str:
        return (
            "Return two code blocks in this order:\n"
            "1. One complete Java file inside a single ```java``` block.\n"
            "2. One valid JSON object inside a single ```json``` block with this shape:\n"
            '{"method_name":"...", "param_example":{...}}'
        )

    def validate_generated_code(self, source_code: str) -> tuple[bool, str]:
        class_name_match = PUBLIC_CLASS_RE.search(source_code)
        if not class_name_match:
            return False, "Could not find a public class declaration in generated code."

        class_name = class_name_match.group(1)
        try:
            with tempfile.TemporaryDirectory(prefix="eternity-java-agent-") as temp_dir:
                java_path = Path(temp_dir) / f"{class_name}.java"
                java_path.write_text(source_code, encoding="utf-8")
                self.compiler.compileJavaFile(str(java_path))
                class_file = java_path.with_suffix(".class")
                class_size = class_file.stat().st_size if class_file.exists() else 0
        except Exception as exc:  # pragma: no cover - runtime path
            return False, str(exc)

        return True, f"Compilation succeeded for {class_name}.class ({class_size} bytes)."

    def extract_result_metadata(
        self,
        raw_response: str,
        generated_code: str,
    ) -> dict[str, object]:
        metadata = extract_json_block(raw_response)
        method_name = metadata.get("method_name")
        if not isinstance(method_name, str) or not method_name.strip():
            method_name = infer_method_name(generated_code)
        else:
            method_name = method_name.strip()

        param_example = metadata.get("param_example")
        if not isinstance(param_example, dict):
            if isinstance(metadata, dict) and "param_example" not in metadata:
                # Allow a bare JSON object as the param example.
                param_example = {
                    key: value for key, value in metadata.items() if isinstance(key, str)
                }
            else:
                param_example = {}

        if not param_example:
            param_example = infer_param_example(generated_code)

        return {
            "method_name": method_name,
            "param_example": param_example,
        }

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from .base_payload_agent import BasePayloadAgent, PayloadAgentConfig


PHP_BLOCK_RE = re.compile(r"```php\s*(.*?)```", re.IGNORECASE | re.DOTALL)
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1] / "php" / "payload" / "sayHello.php"
)


def extract_php_code(content: str) -> str:
    match = PHP_BLOCK_RE.search(content)
    if match:
        return match.group(1).strip()
    return content.strip()


class PhpPayloadAgent(BasePayloadAgent):
    prompt_relative_path = "php/payload_system.md"
    output_language = "php"

    def __init__(
        self,
        config: PayloadAgentConfig,
        template_path: Path | None = None,
    ) -> None:
        self.template_path = template_path or TEMPLATE_PATH
        self.template_source = self.template_path.read_text(encoding="utf-8")
        super().__init__(config)

    def _build_system_prompt(self) -> str:
        prompt_template = self._read_prompt()
        return prompt_template.format(template_source=self.template_source)

    def extract_generated_code(self, content: str) -> str:
        return extract_php_code(content)

    def validate_generated_code(self, source_code: str) -> tuple[bool, str]:
        lint_source = source_code
        if not lint_source.lstrip().startswith("<?php"):
            lint_source = "<?php\n" + lint_source

        try:
            with tempfile.TemporaryDirectory(prefix="eternity-php-agent-") as temp_dir:
                php_path = Path(temp_dir) / "payload.php"
                php_path.write_text(lint_source, encoding="utf-8")
                proc = subprocess.run(
                    ["php", "-l", str(php_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
        except Exception as exc:  # pragma: no cover - runtime path
            return False, str(exc)

        if proc.returncode != 0:
            error_output = proc.stderr.strip() or proc.stdout.strip()
            return False, f"PHP lint failed: {error_output}"

        message = proc.stdout.strip() or "PHP lint succeeded."
        return True, message

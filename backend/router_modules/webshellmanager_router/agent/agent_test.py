from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    backend_dir = Path(__file__).resolve().parents[3]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from router_modules.webshellmanager_router.agent import (
        JavaPayloadAgent,
        JspDisguiseAgent,
        JspxDisguiseAgent,
        PayloadAgentConfig,
        PhpDisguiseAgent,
        PhpPayloadAgent,
    )
else:
    from . import (
        JavaPayloadAgent,
        JspDisguiseAgent,
        JspxDisguiseAgent,
        PayloadAgentConfig,
        PhpDisguiseAgent,
        PhpPayloadAgent,
    )


DEFAULT_REQUIREMENT = (
    "Generate a Java payload based on PayloadTemplate.java. "
    "Add methodName `sayHello` that reads the `name` parameter and returns "
    "`ok:Hello, <name>!`."
)
DEFAULT_PHP_REQUIREMENT = (
    "Generate a PHP payload that adds methodName `sayHello`, reads the `name` "
    "parameter, and returns `ok:Hello, <name>!`."
)
DEFAULT_JSP_DISGUISE_REQUIREMENT = (
    "Generate a JSP webshell disguised as a normal database administration business page."
)
DEFAULT_PHP_DISGUISE_REQUIREMENT = (
    "Generate a PHP webshell disguised as a normal user authentication module."
)
DEFAULT_JSPX_DISGUISE_REQUIREMENT = (
    "Generate a JSPX webshell disguised as a normal cache management service."
)
DEFAULT_PROVIDER = "gemini_proxy"
DEFAULT_OPENAI_BASE_URL = "https://code.newcli.com/gemini"
DEFAULT_OPENAI_MODEL = "gemini-3-pro"
DEFAULT_LLM_MODEL = "gemini-3.1-pro"
DEFAULT_LLM_BASE_URL = "https://code.newcli.com/gemini"
DEFAULT_LLM_API_KEY = ""


AGENT_TYPES = {
    "java_payload": JavaPayloadAgent,
    "php_payload": PhpPayloadAgent,
    "jsp_disguise": JspDisguiseAgent,
    "jspx_disguise": JspxDisguiseAgent,
    "php_disguise": PhpDisguiseAgent,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a LangGraph smoke test for payload generation."
    )
    parser.add_argument(
        "--agent-type",
        choices=sorted(AGENT_TYPES),
        default=os.getenv("PAYLOAD_AGENT_TYPE", "java_payload"),
        help="Payload agent type. Defaults to PAYLOAD_AGENT_TYPE or java_payload.",
    )
    parser.add_argument(
        "--requirement",
        default="",
        help="Natural-language requirement for the payload.",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "codex_proxy", "gemini_proxy"],
        default=os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER),
        help="LLM provider type. Defaults to LLM_PROVIDER or codex_proxy.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("LLM_API_KEY", DEFAULT_LLM_API_KEY),
        help="LLM API key. Defaults to LLM_API_KEY.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("LLM_BASE_URL", ""),
        help="OpenAI-compatible base URL. Defaults to LLM_BASE_URL.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", ""),
        help="Model name. Defaults to LLM_MODEL.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        help="Sampling temperature. Defaults to 0.1.",
    )
    parser.add_argument(
        "--max-compile-attempts",
        type=int,
        default=int(os.getenv("AGENT_MAX_COMPILE_ATTEMPTS", "3")),
        help="Maximum compile-repair attempts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the final result as JSON.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    requirement = args.requirement
    if not requirement:
        requirement = DEFAULT_REQUIREMENT
        if args.agent_type == "php_payload":
            requirement = DEFAULT_PHP_REQUIREMENT
        elif args.agent_type == "jsp_disguise":
            requirement = DEFAULT_JSP_DISGUISE_REQUIREMENT
        elif args.agent_type == "php_disguise":
            requirement = DEFAULT_PHP_DISGUISE_REQUIREMENT
        elif args.agent_type == "jspx_disguise":
            requirement = DEFAULT_JSPX_DISGUISE_REQUIREMENT

    default_base_url = DEFAULT_LLM_BASE_URL
    default_model = DEFAULT_LLM_MODEL
    if args.provider == "openai":
        default_base_url = DEFAULT_OPENAI_BASE_URL
        default_model = DEFAULT_OPENAI_MODEL

    api_key = args.api_key
    base_url = args.base_url or default_base_url
    model_name = args.model or default_model

    if not api_key:
        print("Missing API key. Use --api-key or set ETERNITY_LLM_API_KEY.", file=sys.stderr)
        return 2

    if not model_name:
        print("Missing model name. Use --model or set ETERNITY_LLM_MODEL.", file=sys.stderr)
        return 2

    agent_cls = AGENT_TYPES[args.agent_type]
    agent = agent_cls(
        PayloadAgentConfig(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            provider=args.provider,
            temperature=args.temperature,
            max_compile_attempts=args.max_compile_attempts,
        )
    )
    result = agent.run(requirement)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        """ print(f"compile_success: {result['compile_success']}")
        print(f"compile_attempts: {result['compile_attempts']}")
        print(f"compile_message: {result['compile_message']}") """
        print("\nGenerated code:\n")
        print(result["generated_code"])

    return 0 if result["compile_success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

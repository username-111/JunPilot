import asyncio
import difflib
import json
import logging
import os
import re
import time
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

TASK_TYPES = {"generate_code", "write_tests", "fix_error", "refactor"}
DEFAULT_TASK_TYPE = "generate_code"
DEFAULT_MODEL = "deepseek-r1:14b"
OLLAMA_URL = "http://localhost:11434/api/generate"
AUTO_DIFF_ENABLED = True


def _setup_logger() -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("mcp_ollama")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        file_handler = logging.FileHandler(log_dir / "mcp_ollama.log", encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


logger = _setup_logger()

app = Server("ollama-coder")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="local_code_assistant",
            description=(
                "ЛОКАЛЬНЫЙ ИНСТРУМЕНТ-ИСПОЛНИТЕЛЬ для задач кодинга. Передавай intent "
                "пользователя максимально близко к оригиналу и не решай задачу заранее "
                "на стороне Copilot. Используй task_type для режима работы: generate_code, "
                "write_tests, fix_error, refactor. Возвращает компактный JSON результат."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Intent пользователя (передавай почти verbatim)"
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["generate_code", "write_tests", "fix_error", "refactor"],
                        "description": "Режим исполнения локальной LLM",
                        "default": "generate_code"
                    },
                    "context": {
                        "type": "string",
                        "description": "Общий контекст задачи",
                        "default": ""
                    },
                    "requirements": {
                        "type": "string",
                        "description": "Явные требования к результату",
                        "default": ""
                    },
                    "existing_code": {
                        "type": "string",
                        "description": "Текущий код до изменений",
                        "default": ""
                    },
                    "tests": {
                        "type": "string",
                        "description": "Тесты или требования к тестам",
                        "default": ""
                    },
                    "runtime_errors": {
                        "type": "string",
                        "description": "Текущие runtime/lint/test ошибки",
                        "default": ""
                    },
                    "language_hint": {
                        "type": "string",
                        "description": "Подсказка языка (python/js/sql/etc)",
                        "default": ""
                    },
                    "prefer_diff": {
                        "type": "boolean",
                        "description": "Предпочитать unified diff при наличии existing_code",
                        "default": False
                    }
                },
                "required": ["prompt"]
            }
        )
    ]


def normalize_task_type(task_type: str) -> str:
    if task_type in TASK_TYPES:
        return task_type
    return DEFAULT_TASK_TYPE


def build_task_prompt(
    task_type: str,
    prompt: str,
    context: str,
    requirements: str,
    existing_code: str,
    tests: str,
    runtime_errors: str,
    language_hint: str,
) -> str:
    normalized = normalize_task_type(task_type)
    task_instructions = {
        "generate_code": "Generate only the required code change.",
        "write_tests": "Write only focused tests required by the request.",
        "fix_error": "Fix the reported errors with minimal changes.",
        "refactor": "Refactor while preserving behavior and scope.",
    }

    parts = [
        "You are a code execution worker.",
        "Return content only. No chain-of-thought. No preamble.",
        f"TASK_TYPE: {normalized}",
        f"TASK_RULE: {task_instructions[normalized]}",
        "USER_INTENT:",
        prompt.strip(),
    ]

    optional_sections = [
        ("CONTEXT", context),
        ("REQUIREMENTS", requirements),
        ("EXISTING_CODE", existing_code),
        ("TESTS", tests),
        ("RUNTIME_ERRORS", runtime_errors),
        ("LANGUAGE_HINT", language_hint),
    ]
    for section_name, section_value in optional_sections:
        if section_value:
            parts.extend([f"{section_name}:", section_value.strip()])

    parts.extend(
        [
            "OUTPUT_CONSTRAINTS:",
            "- Produce only the final code/result content.",
            "- Do not include explanations outside code comments.",
            "- Keep edits minimal and task-focused.",
        ]
    )
    return "\n".join(parts)


def make_unified_diff(existing_code: str, generated_code: str) -> str:
    diff_lines = difflib.unified_diff(
        existing_code.splitlines(keepends=True),
        generated_code.splitlines(keepends=True),
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "\n".join(diff_lines)


def select_output_content(
    generated_code: str,
    existing_code: str,
    prefer_diff: bool,
    auto_diff_enabled: bool = AUTO_DIFF_ENABLED,
) -> tuple[str, str]:
    if not existing_code:
        return generated_code, "full"

    diff_content = make_unified_diff(existing_code, generated_code)
    should_use_diff = prefer_diff or (auto_diff_enabled and len(diff_content) < len(generated_code))

    if should_use_diff and diff_content:
        return diff_content, "diff"
    return generated_code, "full"


def summarize_result(task_type: str, output_format: str, content: str) -> str:
    size_hint = len(content)
    return f"{task_type}:{output_format}:{size_hint}"


def build_result_payload(
    task_type: str,
    language: str,
    content: str,
    output_format: str,
    tokens_used: int | None = None,
) -> dict:
    return {
        "result_type": "success",
        "language": language or "text",
        "content": content,
        "summary": summarize_result(task_type, output_format, content),
        "format": output_format,
        "task_type": normalize_task_type(task_type),
        "tokens_used": tokens_used,
    }


def build_error_payload(task_type: str, message: str, error_class: str) -> dict:
    return {
        "result_type": "error",
        "language": "text",
        "content": "",
        "summary": message,
        "format": "none",
        "task_type": normalize_task_type(task_type),
        "tokens_used": None,
        "error_class": error_class,
    }

def extract_final_answer(text: str) -> str:
    """DeepSeek R1 возвращает <think>...</think> + ответ. Убираем reasoning."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cleaned = cleaned.lstrip("\n")
    return cleaned


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "local_code_assistant":
        raise ValueError(f"Unknown tool: {name}")

    prompt = arguments.get("prompt", "")
    context = arguments.get("context", "")
    requirements = arguments.get("requirements", "")
    existing_code = arguments.get("existing_code", "")
    tests = arguments.get("tests", "")
    runtime_errors = arguments.get("runtime_errors", "")
    language_hint = arguments.get("language_hint", "")
    prefer_diff = bool(arguments.get("prefer_diff", False))
    task_type = normalize_task_type(arguments.get("task_type", DEFAULT_TASK_TYPE))
    model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)

    full_prompt = build_task_prompt(
        task_type=task_type,
        prompt=prompt,
        context=context,
        requirements=requirements,
        existing_code=existing_code,
        tests=tests,
        runtime_errors=runtime_errors,
        language_hint=language_hint,
    )

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 4096,
                        "top_p": 0.9,
                        "stop": ["<|im_end|>"],
                    },
                },
            )
            response.raise_for_status()
            response_json = response.json()

        raw_result = response_json.get("response", "")
        final_result = extract_final_answer(raw_result)
        selected_content, selected_format = select_output_content(
            generated_code=final_result,
            existing_code=existing_code,
            prefer_diff=prefer_diff,
        )
        tokens_used = response_json.get("eval_count")

        payload = build_result_payload(
            task_type=task_type,
            language=language_hint or "text",
            content=selected_content,
            output_format=selected_format,
            tokens_used=tokens_used,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "tool=%s model=%s task_type=%s prompt_len=%d context_len=%d response_len=%d format=%s latency_ms=%d",
            name,
            model,
            task_type,
            len(prompt),
            len(context),
            len(selected_content),
            selected_format,
            latency_ms,
        )
        return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]
    except httpx.TimeoutException as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.error(
            "tool=%s model=%s task_type=%s error=timeout prompt_len=%d context_len=%d latency_ms=%d message=%s",
            name,
            model,
            task_type,
            len(prompt),
            len(context),
            latency_ms,
            str(exc),
        )
        payload = build_error_payload(task_type, "Ollama request timed out", "timeout")
        return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]
    except httpx.HTTPStatusError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.error(
            "tool=%s model=%s task_type=%s error=http_status prompt_len=%d context_len=%d latency_ms=%d status=%d message=%s",
            name,
            model,
            task_type,
            len(prompt),
            len(context),
            latency_ms,
            exc.response.status_code,
            str(exc),
        )
        payload = build_error_payload(task_type, "Ollama returned HTTP error", "http_status")
        return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]
    except httpx.RequestError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.error(
            "tool=%s model=%s task_type=%s error=connection prompt_len=%d context_len=%d latency_ms=%d message=%s",
            name,
            model,
            task_type,
            len(prompt),
            len(context),
            latency_ms,
            str(exc),
        )
        payload = build_error_payload(task_type, "Ollama connection error", "connection")
        return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "tool=%s model=%s task_type=%s error=internal prompt_len=%d context_len=%d latency_ms=%d",
            name,
            model,
            task_type,
            len(prompt),
            len(context),
            latency_ms,
        )
        payload = build_error_payload(task_type, "Internal executor error", "internal")
        return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
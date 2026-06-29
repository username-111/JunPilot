# mcp_ollama_server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
import httpx
import asyncio
import re
import time

app = Server("ollama-coder")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="local_code_assistant",
            description=(
                "ЛОКАЛЬНЫЙ ИНСТРУМЕНТ для задач кодинга. ИСПОЛЬЗУЙ ДЛЯ ЛЮБЫХ "
                "задач, связанных с кодом: написание функций, рефакторинг, тесты, "
                "документация, исправление багов, форматирование, добавление type hints, "
                "генерация regex, bash-скриптов, SQL-запросов, конфигов. "
                "Работает на deepseek-r1:14b — быстро и качественно на локальном GPU. "
                "НЕ ИСПОЛЬЗУЙ только для: планирования архитектуры всего проекта, "
                "анализа бизнес-требований, работы с внешними API без документации, "
                "сложных меж-модульных интеграций требующих контекста всей кодовой базы."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Детальное описание задачи для локальной LLM"
                    },
                    "context": {
                        "type": "string",
                        "description": "Контекст: фрагменты кода, ошибки, требования",
                        "default": ""
                    }
                },
                "required": ["prompt"]
            }
        )
    ]

def extract_final_answer(text: str) -> str:
    """DeepSeek R1 возвращает <think>...</think> + ответ. Убираем reasoning."""
    # Удаляем блок <think>...</think>
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Убираем лишние пустые строки в начале
    cleaned = cleaned.lstrip('\n')
    return cleaned

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    print("=" * 80)
    print(time.strftime("%H:%M:%S"))
    print("PROMPT:")
    print(arguments.get("prompt"))
    print("=" * 80)

    if name != "local_code_assistant":
        raise ValueError(f"Unknown tool: {name}")
    
    prompt = arguments.get("prompt", "")
    context = arguments.get("context", "")
    сontext = ('Контекст:\n' + context) if context else ''
    
    full_prompt = f"""Ты — опытный разработчик. Дай ТОЛЬКО результат, без объяснений процесса.

Задача:
{prompt}

{context}

Важно:
- Отвечай сразу готовым кодом или решением
- Без вступлений и заключений вроде "Вот решение:"
- Если нужно объяснить — делай это в комментариях к коду
"""
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:14b",
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,      # Низкая температура для кода
                    "num_predict": 4096,     # Больше токенов для сложных задач
                    "top_p": 0.9,
                    "stop": ["<|im_end|>"]   # Стоп-токен если есть
                }
            },
            timeout=180.0
        )
        
        raw_result = response.json()["response"]
        final_result = extract_final_answer(raw_result)
    
    return [TextContent(type="text", text=final_result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
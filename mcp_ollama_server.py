# mcp_ollama_server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
import httpx
import asyncio

app = Server("ollama-coder")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="code_with_ollama",
            description="Генерация и рефакторинг кода через локальную LLM (Ollama)",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Запрос для генерации кода"
                    },
                    "model": {
                        "type": "string",
                        "description": "Модель Ollama (по умолчанию: codellama:7b-code)",
                        "default": "codellama:7b-code"
                    }
                },
                "required": ["prompt"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "code_with_ollama":
        raise ValueError(f"Unknown tool: {name}")
    
    prompt = arguments.get("prompt")
    model = arguments.get("model", "codellama:7b-code")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 2048
                }
            },
            timeout=120.0
        )
        result = response.json()["response"]
    
    return [TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
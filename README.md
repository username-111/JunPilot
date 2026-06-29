# JunPilot

JunPilot is a local MCP server that exposes an Ollama-backed coding assistant tool. It is designed to help other agents or clients generate code, write tests, fix errors, and perform focused refactors while keeping the work local.

## Features

- Exposes a single MCP tool named `local_code_assistant`
- Builds structured prompts for different coding task types
- Supports optional diff output when existing code is provided
- Writes runtime logs to `logs/mcp_ollama.log`

## Requirements

- Python 3.10 or newer
- An Ollama instance running at `http://localhost:11434`
- The `mcp` and `httpx` Python packages

## Installation

Create and activate a virtual environment, then install the project dependencies:

```bash
pip install -U pip
pip install mcp httpx
```

If you prefer to work from the project metadata, you can also install dependencies with your usual Python workflow once the environment is configured.

## Running the server

Start the MCP server directly with Python:

```bash
python mcp_ollama_server.py
```

By default, the server uses the Ollama model `deepseek-r1:14b`. You can override it with the `OLLAMA_MODEL` environment variable.

## Configuration

- `OLLAMA_MODEL`: overrides the default Ollama model name
- `AUTO_DIFF_ENABLED`: controls whether smaller unified diffs may be returned when existing code is supplied

## Tests

Run the test suite with:

```bash
python -m pytest tests
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the full text.
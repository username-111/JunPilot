# JunPilot

JunPilot is a local MCP server that exposes an Ollama-backed coding assistant tool. It is designed to help other agents or clients generate code, write tests, fix errors, and perform focused refactors while keeping the work local. It also helps reduce cloud LLM token usage by delegating routine coding tasks to a lighter but effectively unlimited local model.

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

### Install this MCP server in VS Code

1. Make sure your virtual environment is active and dependencies are installed.
2. Open VS Code Settings JSON (Command Palette -> Preferences: Open User Settings (JSON)).
3. Add an MCP server entry that starts this script with your local Python interpreter.

Example configuration:

```json
{
	"chat.mcp.servers": {
		"junpilot-local": {
			"command": "path/to/Your/.venv/Scripts/python.exe",
			"args": [
				"path/to/JunPilot/mcp_ollama_server.py"
			]
		}
	}
}
```

Adjust the paths to match your machine. After saving settings, reload VS Code if the server does not appear immediately.

## Running the server

Start the MCP server directly with Python:

```bash
python mcp_ollama_server.py
```

By default, the server uses the Ollama model `deepseek-r1:14b`. You can override it with the `OLLAMA_MODEL` environment variable.

## Configuration

- `OLLAMA_MODEL`: overrides the default Ollama model name
- `AUTO_DIFF_ENABLED`: controls whether smaller unified diffs may be returned when existing code is supplied

## Using the global prompt for delegation

This repository includes a delegation instruction file at `.github/copilot-instructions.md`. Its purpose is to push Copilot to route direct coding tasks to the local MCP tool (`local_code_assistant`) instead of spending cloud model tokens on routine implementation work.

Recommended workflow:

1. Keep `.github/copilot-instructions.md` in the repository so it is loaded as project-level guidance.
2. Ensure the MCP server is running and visible in VS Code.
3. Ask for coding tasks normally (for example: "write a function", "refactor this file", "add unit tests").
4. Copilot will follow the prompt policy and delegate those routine coding tasks to the local Ollama-backed tool.

Use cloud reasoning for architecture decisions, business analysis, and unfamiliar external API planning, while offloading routine code generation to the local model.

## Tests

Run the test suite with:

```bash
python -m pytest tests
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the full text.
## Plan: MCP Ollama Executor Upgrade

TL;DR (RU): Сохраняем простой MCP stdio сервер, но переводим local_code_assistant в режим «исполнитель», добавляем task_type, компактный JSON-ответ, режим авто-diff и операционное логирование в logs/mcp_ollama.log. Copilot остаётся планировщиком/интегратором, локальная LLM — генератором изменений.
TL;DR (EN): Keep the server as a simple MCP stdio tool, but turn local_code_assistant into an execution-oriented worker with task_type, compact JSON response, auto diff mode, and production logging to logs/mcp_ollama.log. Copilot remains planner/integrator; local LLM is the code executor.

**Steps**
1. Phase 1 — Input/Output Contract Redesign
1.1 Update tool description in c:\Users\Masha\PycharmProjects\JunPilot\mcp_ollama_server.py to explicitly instruct Copilot to pass user intent almost verbatim and avoid pre-solving.
1.2 Extend inputSchema with task_type enum (generate_code, write_tests, fix_error, refactor), plus optional fields for TDD loop: requirements, existing_code, tests, runtime_errors, language_hint, prefer_diff.
1.3 Define structured output JSON fields: result_type, language, content, summary, format, task_type, tokens_used(optional if available). Keep summary short and content-only.
1.4 Keep backwards compatibility: if missing task_type, default to generate_code.

2. Phase 2 — Prompt Builder by Task Type (depends on 1)
2.1 Add a prompt composition helper that maps task_type to concise instruction templates.
2.2 Ensure templates request only necessary changes and no chain-of-thought/explanations.
2.3 For TDD mode, include only provided sections (requirements/code/tests/errors) and avoid boilerplate text inflation.
2.4 Fix context concatenation bug (variable with Cyrillic character) while consolidating prompt assembly.

3. Phase 3 — Diff-First Output Optimization (depends on 1, parallel with 2 after schema defined)
3.1 Add helper to compare full content length vs unified diff length when existing_code is provided.
3.2 If prefer_diff is true or auto mode enabled and diff is smaller, return format=diff and diff content.
3.3 Otherwise return full content with format=full.
3.4 Keep deterministic behavior and avoid expensive post-processing.

4. Phase 4 — Logging and Reliability (parallel with 2/3 except where fields depend on output)
4.1 Configure Python logging with FileHandler for logs/mcp_ollama.log, create logs directory if missing.
4.2 Log per-call metadata: timestamp, tool name, prompt length, context length, response length, ollama latency ms, model, task_type, selected output format.
4.3 Add robust HTTP error and timeout handling for Ollama call (httpx timeout, status errors, connection errors), with error class and message logged.
4.4 Return compact user-safe error payloads while preserving detailed diagnostics in log file.

5. Phase 5 — Configuration and Minimal Surface (depends on 4)
5.1 Make model configurable via environment variable OLLAMA_MODEL with default deepseek-r1:14b.
5.2 Keep server architecture as single-file stdio MCP server; avoid extra services/queues.
5.3 Keep dependencies minimal (stdlib logging + existing httpx/mcp).

6. Phase 6 — Verification (depends on all prior phases)
6.1 Static check: run server startup and confirm tool schema includes task_type and TDD fields.
6.2 Functional checks by mode: generate_code, write_tests, fix_error, refactor.
6.3 TDD cycle check: send requirements+code+tests+runtime_errors and verify only necessary changes are returned.
6.4 Diff behavior check: confirm format switches to diff when shorter.
6.5 Observability check: validate log lines in logs/mcp_ollama.log include all required metrics and error cases.

**Relevant files**
- c:\Users\Masha\PycharmProjects\JunPilot\mcp_ollama_server.py — main MCP tool definition, schema, prompt assembly, Ollama call, response shaping, error handling, logging.
- c:\Users\Masha\PycharmProjects\JunPilot\pyproject.toml — optional dependency updates only if needed (likely none).
- c:\Users\Masha\PycharmProjects\JunPilot\logs\mcp_ollama.log — runtime log target (created at runtime).

**Verification**
1. Start server and inspect MCP tool metadata to confirm updated description and schema fields.
2. Invoke local_code_assistant with each task_type and verify structured JSON output contract.
3. Force timeout/HTTP failure against Ollama endpoint and confirm error logging + compact error response.
4. Run one TDD loop scenario end-to-end and validate response is minimal change-oriented.
5. Compare payload sizes for full vs diff mode in at least one sample edit.

**Decisions**
- Response format: strict JSON (selected).
- Diff strategy: auto-select diff when shorter (selected), with optional prefer_diff override.
- Model config: environment-configurable default model (selected).
- In scope: MCP schema/prompting/logging/output optimization.
- Out of scope: replacing cloud model, multi-process architecture, persistent task queue.

**Further Considerations**
1. Security/Privacy note: logs may capture sensitive code fragments indirectly via lengths and error text; avoid storing raw prompts/responses by default, and keep log file local-only.
2. Potential extension: add request_id correlation id for easier tracing across repeated TDD iterations.
3. If Ollama supports token counters in response metadata, map them to tokens_used; otherwise keep null.
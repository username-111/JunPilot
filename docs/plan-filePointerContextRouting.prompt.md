## Plan: File Pointer Context Routing

TL;DR (RU): Добавляется режим «указателей на файлы», где облачная часть решает, когда передавать ссылки вместо текста (path + ranges), насколько расширять контекст, и как балансировать полноту контекста с экономией облачных токенов. MCP-сервер обязан уметь локально разворачивать указатели в текст для локальной LLM. Экономия токенов локальной модели не является целевой метрикой.
TL;DR (EN): Add a file-pointer mode where the cloud side decides when to send references instead of raw file content, how much to expand context, and how to trade off completeness vs cloud token savings. MCP server must resolve pointers locally into text for local LLM. Local-model token savings are not a target metric.

**Steps**
1. Define pointer-aware request contract for local_code_assistant
1.1 Add optional pointer fields: file_refs[] with items {path, start_line, end_line, role}.
1.2 Add context-expansion hints from cloud: expansion_policy (none|minimal|balanced|aggressive), surrounding_lines, max_chars_per_ref, max_total_chars.
1.3 Keep compatibility with existing raw context field.

2. Cloud-side decision policy (planner responsibility)
2.1 Use pointers when raw code would significantly increase cloud prompt size.
2.2 Use inline content only for tiny snippets or when precision-critical areas are ambiguous.
2.3 Select expansion depth by task_type and uncertainty:
- generate_code/refactor: balanced/aggressive for dependency awareness.
- write_tests/fix_error: minimal/balanced with focus near failures and tested surfaces.
2.4 Before sending request, estimate local prompt size against available local context window and downgrade/trim refs if needed.

3. MCP pointer resolution behavior (executor responsibility)
3.1 Validate paths and line ranges; reject unsafe traversal.
3.2 Read referenced file slices locally and apply expansion policy.
3.3 Assemble resolved context in deterministic order and include truncation metadata if limits are hit.
3.4 Continue sending assembled prompt to Ollama; return compact structured output.

4. Optimization target and constraints
4.1 Primary objective: reduce cloud-side token usage.
4.2 Secondary objective: preserve output quality via adaptive expansion.
4.3 Non-objective: minimizing local LLM tokens.
4.4 Hard guardrail: never exceed configured local context window budget.

5. Observability requirements
5.1 Log pointer_count, resolved_chars, truncated_refs_count, expansion_policy, local_window_budget, local_window_used.
5.2 Log cloud-savings proxy metrics: raw_context_chars_estimate vs pointer_payload_chars.
5.3 Log resolver errors: missing files, invalid ranges, oversized requests.

6. Verification
6.1 Compare cloud payload sizes for identical tasks with raw context vs pointers.
6.2 Validate quality parity on representative tasks (generate_code, write_tests, fix_error, refactor).
6.3 Stress-test near local context window limit and verify graceful truncation.
6.4 Confirm no path traversal and invalid-range handling.

**Relevant files**
- c:\Users\Masha\PycharmProjects\JunPilot\mcp_ollama_server.py — schema extension, pointer resolver, context assembly, guards, logging.
- c:\Users\Masha\PycharmProjects\JunPilot\docs\plan-mcpOllamaExecutorUpgrade.prompt.md — main plan reference.
- c:\Users\Masha\PycharmProjects\JunPilot\logs\mcp_ollama.log — observability output.

**Decisions**
- Cloud decides pointer usage and expansion depth.
- MCP resolves pointers locally and enforces safety/window constraints.
- Priority metric is cloud token reduction, not local token reduction.
- Cloud planner must account for local context window before issuing pointer-based requests.

**Further Considerations**
1. Add optional semantic anchors later (symbol/function selectors) to reduce brittle line-based refs.
2. Introduce request_id to correlate planning decision and resolver outcome in logs.
3. Keep pointer contract minimal initially; avoid introducing indexing service.
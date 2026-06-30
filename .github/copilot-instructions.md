# Delegation Instructions

## Delegation Rule
For ALL tasks that involve direct code work, use the `local_code_assistant` tool.
Use cloud models only for:
- Initial project structure planning
- Business logic and requirements analysis
- Work with external APIs that lack documentation
- Complex cross-module dependencies that require full codebase context

## What to Use and When
| Task | Tool |
|------|------|
| Writing a function/class | local_code_assistant |
| Refactoring | local_code_assistant |
| Unit tests | local_code_assistant |
| Docstrings, comments | local_code_assistant |
| Fixing lint errors | local_code_assistant |
| Code review of a specific file | local_code_assistant |
| Module architecture planning | Copilot (cloud) |
| Technology stack selection | Copilot (cloud) |
| Integration with an unfamiliar API | Copilot (cloud) |
import mcp_ollama_server as server


def test_build_task_prompt_fallbacks_to_generate_code():
    prompt = server.build_task_prompt(
        task_type="unknown",
        prompt="Implement parser",
        context="",
        requirements="",
        existing_code="",
        tests="",
        runtime_errors="",
        language_hint="",
    )

    assert "TASK_TYPE: generate_code" in prompt


def test_build_task_prompt_includes_only_non_empty_sections():
    prompt = server.build_task_prompt(
        task_type="write_tests",
        prompt="Add tests for calculator",
        context="module calc.py",
        requirements="cover edge cases",
        existing_code="",
        tests="",
        runtime_errors="",
        language_hint="python",
    )

    assert "CONTEXT:" in prompt
    assert "REQUIREMENTS:" in prompt
    assert "LANGUAGE_HINT:" in prompt
    assert "EXISTING_CODE:" not in prompt
    assert "TESTS:" not in prompt
    assert "RUNTIME_ERRORS:" not in prompt


def test_select_output_content_returns_diff_when_preferred_and_existing_code_present():
    existing_code = "def add(a, b):\n    return a+b\n"
    generated_code = "def add(a, b):\n    return a + b\n"

    content, output_format = server.select_output_content(
        generated_code=generated_code,
        existing_code=existing_code,
        prefer_diff=True,
    )

    assert output_format == "diff"
    assert "@@" in content


def test_select_output_content_returns_full_when_existing_code_missing():
    generated_code = "print('ok')\n"

    content, output_format = server.select_output_content(
        generated_code=generated_code,
        existing_code="",
        prefer_diff=True,
    )

    assert output_format == "full"
    assert content == generated_code


def test_build_result_payload_has_required_fields():
    payload = server.build_result_payload(
        task_type="refactor",
        language="python",
        content="def fn():\n    pass\n",
        output_format="full",
        tokens_used=123,
    )

    assert payload["result_type"] == "success"
    assert payload["language"] == "python"
    assert payload["content"]
    assert payload["summary"]
    assert payload["format"] == "full"
    assert payload["task_type"] == "refactor"
    assert payload["tokens_used"] == 123

"""Usage token normalization tests for OpenAI-compatible providers."""

from app.provider.openai_compat import _extract_usage_tokens


def test_extract_usage_tokens_prompt_details_format():
    usage = {
        "prompt_tokens": 194,
        "completion_tokens": 12,
        "total_tokens": 206,
        "prompt_tokens_details": {
            "cached_tokens": 24,
            "cache_write_tokens": 10,
        },
        "completion_tokens_details": {
            "reasoning_tokens": 7,
        },
    }

    normalized = _extract_usage_tokens(usage)

    assert normalized == {
        "input": 170,
        "output": 5,
        "reasoning": 7,
        "cache_read": 24,
        "cache_write": 10,
        "total": 206,
    }


def test_extract_usage_tokens_legacy_cache_fields():
    usage = {
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "total_tokens": 150,
        "cache_read_input_tokens": 40,
        "cache_creation_input_tokens": 8,
    }

    normalized = _extract_usage_tokens(usage)

    assert normalized["input"] == 120
    assert normalized["output"] == 30
    assert normalized["reasoning"] == 0
    assert normalized["cache_read"] == 40
    assert normalized["cache_write"] == 8
    assert normalized["total"] == 150


def test_extract_usage_tokens_falls_back_total_when_missing():
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "prompt_tokens_details": {"cached_tokens": 25},
    }

    normalized = _extract_usage_tokens(usage)

    assert normalized["input"] == 75
    assert normalized["cache_read"] == 25
    assert normalized["total"] == 120


def test_extract_usage_tokens_clamps_reasoning_tokens_to_completion():
    usage = {
        "prompt_tokens": 50,
        "completion_tokens": 5,
        "completion_tokens_details": {"reasoning_tokens": 20},
    }

    normalized = _extract_usage_tokens(usage)

    assert normalized["reasoning"] == 5
    assert normalized["output"] == 0

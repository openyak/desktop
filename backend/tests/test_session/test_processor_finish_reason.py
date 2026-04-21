"""Finish-reason contract tests for the session processor."""

from app.session.processor import _normalize_step_finish_reason


def test_normalize_step_finish_reason_maps_tool_calls_to_tool_use() -> None:
    assert _normalize_step_finish_reason("tool_calls") == "tool_use"


def test_normalize_step_finish_reason_preserves_declared_values() -> None:
    assert _normalize_step_finish_reason("stop") == "stop"
    assert _normalize_step_finish_reason("tool_use") == "tool_use"
    assert _normalize_step_finish_reason("length") == "length"
    assert _normalize_step_finish_reason("error") == "error"


def test_normalize_step_finish_reason_rejects_empty_contract_hole() -> None:
    assert _normalize_step_finish_reason("empty") == "error"
    assert _normalize_step_finish_reason(None) == "error"

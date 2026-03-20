"""Token accounting invariants in session processor."""

from app.schemas.provider import ModelCapabilities, ModelInfo, ModelPricing
from app.session.processor import _calculate_step_cost


def _model(prompt_per_million: float, completion_per_million: float) -> ModelInfo:
    return ModelInfo(
        id="test/model",
        name="test",
        provider_id="openrouter",
        capabilities=ModelCapabilities(),
        pricing=ModelPricing(
            prompt=prompt_per_million,
            completion=completion_per_million,
        ),
    )


def test_calculate_step_cost_includes_reasoning_in_completion_pricing():
    model = _model(prompt_per_million=2.0, completion_per_million=8.0)
    usage = {
        "input": 1_000,
        "output": 500,
        "reasoning": 500,
    }

    cost = _calculate_step_cost(usage, model)
    # 1000 * 2e-6 + (500 + 500) * 8e-6 = 0.002 + 0.008
    assert cost == 0.01


def test_calculate_step_cost_zero_when_pricing_unavailable():
    model = _model(prompt_per_million=0.0, completion_per_million=0.0)
    usage = {"input": 1000, "output": 1000, "reasoning": 1000}
    assert _calculate_step_cost(usage, model) == 0.0


def test_calculate_step_cost_with_markup():
    model = _model(prompt_per_million=2.0, completion_per_million=8.0)
    usage = {"input": 1_000, "output": 500, "reasoning": 500}

    raw_cost = _calculate_step_cost(usage, model)
    marked_up = _calculate_step_cost(usage, model, markup_percent=20.0)

    assert raw_cost == 0.01
    assert marked_up == round(0.01 * 1.2, 10)  # $0.012


def test_calculate_step_cost_markup_zero_on_free_model():
    model = _model(prompt_per_million=0.0, completion_per_million=0.0)
    usage = {"input": 1000, "output": 1000, "reasoning": 0}
    assert _calculate_step_cost(usage, model, markup_percent=20.0) == 0.0

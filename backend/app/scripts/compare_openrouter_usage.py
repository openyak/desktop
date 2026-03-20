"""Compare OpenRouter returned usage/cost with local token accounting.

Usage:
    python -m app.scripts.compare_openrouter_usage
    python -m app.scripts.compare_openrouter_usage --model z-ai/glm-4.7-flash --calls 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from openai import AsyncOpenAI

from app.config import Settings
from app.provider.openrouter import OpenRouterProvider


@dataclass
class UsageRow:
    call: int
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    reasoning_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    openrouter_cost: float | None
    local_cost_estimate: float
    delta_usage_minus_local: float | None


def _int(v: object) -> int:
    try:
        return int(v) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def _float_or_none(v: object) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


async def _run(model: str, calls: int, env_file: str | None) -> list[UsageRow]:
    kwargs = {"_env_file": env_file} if env_file else {}
    settings = Settings(**kwargs)
    api_key = settings.openrouter_api_key
    if not api_key:
        raise RuntimeError(
            "OPENYAK_OPENROUTER_API_KEY not found. Set it in environment or backend/.env"
        )

    provider = OpenRouterProvider(api_key, enable_reasoning=True)
    models = await provider.list_models()
    model_info = next((m for m in models if m.id == model), None)
    if model_info is None:
        raise RuntimeError(f"Model not found in OpenRouter list: {model}")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/openyak/desktop",
            "X-Title": "OpenYak",
        },
    )

    rows: list[UsageRow] = []
    try:
        for i in range(calls):
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": "Return exactly this text: token-accounting-check",
                    }
                ],
                temperature=0,
                max_tokens=64,
                extra_body={"reasoning": {"enabled": True}},
            )

            usage = resp.usage
            prompt_tokens = _int(getattr(usage, "prompt_tokens", 0))
            completion_tokens = _int(getattr(usage, "completion_tokens", 0))
            total_tokens = _int(getattr(usage, "total_tokens", 0))

            prompt_details = getattr(usage, "prompt_tokens_details", None) or {}
            completion_details = getattr(usage, "completion_tokens_details", None) or {}

            cache_read_tokens = _int(
                prompt_details.get("cached_tokens", 0)
                if isinstance(prompt_details, dict)
                else getattr(prompt_details, "cached_tokens", 0)
            )
            cache_write_tokens = _int(
                prompt_details.get("cache_write_tokens", 0)
                if isinstance(prompt_details, dict)
                else getattr(prompt_details, "cache_write_tokens", 0)
            )
            reasoning_tokens = _int(
                completion_details.get("reasoning_tokens", 0)
                if isinstance(completion_details, dict)
                else getattr(completion_details, "reasoning_tokens", 0)
            )
            reasoning_tokens = min(max(reasoning_tokens, 0), completion_tokens)

            input_tokens = max(0, prompt_tokens - cache_read_tokens) if prompt_details else prompt_tokens
            output_tokens = max(0, completion_tokens - reasoning_tokens)

            local_cost = (
                input_tokens * float(model_info.pricing.prompt)
                + (output_tokens + reasoning_tokens) * float(model_info.pricing.completion)
            ) / 1_000_000

            openrouter_cost = _float_or_none(getattr(usage, "cost", None))
            delta = (
                (openrouter_cost - local_cost) if openrouter_cost is not None else None
            )

            rows.append(
                UsageRow(
                    call=i + 1,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    reasoning_tokens=reasoning_tokens,
                    cache_read_tokens=cache_read_tokens,
                    cache_write_tokens=cache_write_tokens,
                    openrouter_cost=openrouter_cost,
                    local_cost_estimate=local_cost,
                    delta_usage_minus_local=delta,
                )
            )
    finally:
        await client.close()

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare OpenRouter usage vs local cost")
    parser.add_argument("--model", default="z-ai/glm-4.7-flash")
    parser.add_argument("--calls", type=int, default=2)
    parser.add_argument(
        "--env-file",
        default=str(Path(__file__).resolve().parents[3] / ".env"),
        help="Path to backend .env file",
    )
    args = parser.parse_args()

    rows = asyncio.run(_run(args.model, args.calls, args.env_file))
    print(json.dumps([asdict(r) for r in rows], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

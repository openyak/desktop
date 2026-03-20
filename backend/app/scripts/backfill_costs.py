"""Recalculate costs for all historical messages after pricing bug fix.

This script fixes the critical pricing bug where OpenRouter's per-token prices
were not converted to per-million format, resulting in costs being 1,000,000x too small.

Usage:
    # Dry run (no changes)
    python -m app.scripts.backfill_costs --dry-run

    # Recalculate all messages (use after pricing bug fix)
    python -m app.scripts.backfill_costs --recalculate-all

    # Only fix zero-cost messages with tokens
    python -m app.scripts.backfill_costs
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.message import Message
from app.provider.openrouter import OpenRouterProvider
from app.provider.registry import ProviderRegistry
from app.storage.database import create_engine, create_session_factory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def backfill_message_costs(
    db: AsyncSession,
    registry: ProviderRegistry,
    dry_run: bool = True,
    recalculate_all: bool = False,
    batch_size: int = 1000,
) -> dict[str, int]:
    """Recalculate costs for messages using current pricing.

    Args:
        db: Database session
        registry: Provider registry for pricing lookup
        dry_run: If True, don't commit changes
        recalculate_all: If True, recalculate all messages; if False, only zero-cost
        batch_size: Number of messages to process per batch

    Returns:
        Statistics dict with counts of processed, updated, failed messages
    """
    stats = {
        "total_processed": 0,
        "total_updated": 0,
        "total_failed": 0,
        "total_no_pricing": 0,
    }

    # Build query for assistant messages with tokens
    query = select(Message).where(
        Message.data["role"].as_string() == "assistant",
        Message.data["model_id"].as_string().isnot(None),
    )

    if not recalculate_all:
        # Only process messages with cost=0 but tokens>0
        logger.info("Mode: Only recalculating zero-cost messages with tokens")
    else:
        # Process all messages
        logger.info("Mode: Recalculating ALL message costs")

    # Process in batches
    offset = 0
    batch_num = 0

    while True:
        batch_num += 1
        logger.info(f"Processing batch {batch_num} (offset {offset})")

        # Fetch batch
        batch_query = query.offset(offset).limit(batch_size)
        result = await db.execute(batch_query)
        messages = result.scalars().all()

        if not messages:
            logger.info("No more messages to process")
            break

        batch_updated = 0
        batch_failed = 0
        batch_no_pricing = 0

        for msg in messages:
            stats["total_processed"] += 1

            try:
                # Extract message data
                data = msg.data
                model_id = data.get("model_id")
                tokens = data.get("tokens", {})
                current_cost = data.get("cost", 0.0)

                input_tokens = tokens.get("input", 0)
                output_tokens = tokens.get("output", 0)
                reasoning_tokens = tokens.get("reasoning", 0)
                total_tokens = input_tokens + output_tokens + reasoning_tokens

                # Skip if no tokens
                if total_tokens == 0:
                    continue

                # Skip if not recalculating all and cost > 0
                if not recalculate_all and current_cost > 0:
                    continue

                # Resolve current pricing
                resolved = registry.resolve_model(model_id)
                if not resolved:
                    logger.warning(f"Message {msg.id}: Model {model_id} not found in registry")
                    batch_no_pricing += 1
                    continue

                provider, model_info = resolved

                if not model_info.pricing or (
                    model_info.pricing.prompt == 0 and model_info.pricing.completion == 0
                ):
                    logger.warning(f"Message {msg.id}: No pricing for {model_id}")
                    batch_no_pricing += 1
                    continue

                # Calculate new cost (pricing is now in per-million format)
                new_cost = (
                    input_tokens * model_info.pricing.prompt / 1_000_000
                    + (output_tokens + reasoning_tokens) * model_info.pricing.completion / 1_000_000
                )

                # Update cost
                if new_cost != current_cost:
                    data["cost"] = new_cost
                    msg.data = data

                    if dry_run:
                        logger.debug(
                            f"Message {msg.id} ({model_id}): "
                            f"${current_cost:.6f} → ${new_cost:.6f} "
                            f"({input_tokens} in, {output_tokens} out)"
                        )
                    else:
                        logger.debug(f"Updated message {msg.id}: ${current_cost:.6f} → ${new_cost:.6f}")

                    batch_updated += 1

            except Exception as e:
                logger.error(f"Failed to process message {msg.id}: {e}")
                batch_failed += 1

        # Commit batch if not dry run
        if not dry_run and batch_updated > 0:
            await db.commit()
            logger.info(f"Batch {batch_num}: Committed {batch_updated} updates")
        else:
            logger.info(
                f"Batch {batch_num}: Would update {batch_updated} messages "
                f"({batch_no_pricing} no pricing, {batch_failed} failed)"
            )

        stats["total_updated"] += batch_updated
        stats["total_failed"] += batch_failed
        stats["total_no_pricing"] += batch_no_pricing

        offset += batch_size

    return stats


async def main():
    parser = argparse.ArgumentParser(description="Backfill message costs after pricing bug fix")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making changes (default: False)",
    )
    parser.add_argument(
        "--recalculate-all",
        action="store_true",
        help="Recalculate all messages (default: only zero-cost messages)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of messages to process per batch (default: 1000)",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("MESSAGE COST BACKFILL SCRIPT")
    logger.info("=" * 60)
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Recalculate all: {args.recalculate_all}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("=" * 60)

    if not args.dry_run:
        confirm = input(
            "\nWARNING: This will modify the database. Are you sure? (yes/no): "
        )
        if confirm.lower() != "yes":
            logger.info("Aborted by user")
            return

    start_time = datetime.now(timezone.utc)

    # Initialize settings and database
    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    # Initialize provider registry
    registry = ProviderRegistry()
    if settings.openrouter_api_key:
        provider = OpenRouterProvider(settings.openrouter_api_key)
        registry.register(provider)
    else:
        logger.error("No OPENROUTER_API_KEY found in environment")
        return

    # Refresh models to get latest pricing
    logger.info("Refreshing model pricing from OpenRouter...")
    try:
        await registry.refresh_models()
        logger.info(f"Loaded {len(registry.all_models())} models")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        return

    # Run backfill with database session
    async with session_factory() as db:
        stats = await backfill_message_costs(
            db=db,
            registry=registry,
            dry_run=args.dry_run,
            recalculate_all=args.recalculate_all,
            batch_size=args.batch_size,
        )

    # Clean up
    await engine.dispose()

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total processed: {stats['total_processed']}")
    logger.info(f"Total updated: {stats['total_updated']}")
    logger.info(f"No pricing available: {stats['total_no_pricing']}")
    logger.info(f"Failed: {stats['total_failed']}")
    logger.info(f"Duration: {duration:.2f}s")

    if args.dry_run:
        logger.info("\n✅ DRY RUN COMPLETED - No changes were made")
        logger.info("Run without --dry-run to apply changes")
    else:
        logger.info("\n✅ BACKFILL COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())

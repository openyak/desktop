/** Pricing conversion utilities for model selector UI. */

/** Markup applied to OpenRouter USD pricing (matches proxy markup_percent: 20.0). */
const MARKUP_MULTIPLIER = 1.2;

/** 1 credit = $0.01 USD. */
const CREDITS_PER_USD = 100;

/** Convert USD-per-million-tokens to credits-per-million-tokens. */
export function usdToCreditsPerM(usdPerM: number): number {
  if (usdPerM <= 0) return 0;
  return Math.ceil(usdPerM * MARKUP_MULTIPLIER * CREDITS_PER_USD);
}

/** Format credits/M for display. Returns e.g. "18 cr/M", "1.8K cr/M", or "FREE". */
export function formatCreditsPerM(creditsPerM: number): string {
  if (creditsPerM === 0) return "FREE";
  if (creditsPerM >= 1000) {
    const k = creditsPerM / 1000;
    return `${k % 1 === 0 ? k.toFixed(0) : k.toFixed(1)}K cr/M`;
  }
  return `${creditsPerM} cr/M`;
}

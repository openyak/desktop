"use client";

import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Check, ChevronDown, Lock, Star } from "lucide-react";
import { useProviderModels } from "@/hooks/use-provider-models";
import { useModelArenaMap, type ArenaScore } from "@/hooks/use-arena-scores";
import { useSettingsStore } from "@/stores/settings-store";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import { API } from "@/lib/constants";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { usdToCreditsPerM, formatCreditsPerM } from "@/lib/pricing";
import type { ModelInfo } from "@/types/model";

/** Short display labels for provider badges in the model list. */
const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Gemini",
  groq: "Groq",
  deepseek: "DeepSeek",
  mistral: "Mistral",
  xai: "xAI",
  together: "Together",
  deepinfra: "DeepInfra",
  cerebras: "Cerebras",
  cohere: "Cohere",
  perplexity: "Perplexity",
  fireworks: "Fireworks",
  azure: "Azure",
  openrouter: "OpenRouter",
  qwen: "Qwen",
  kimi: "Kimi",
  minimax: "MiniMax",
  zhipu: "ZhipuAI",
  siliconflow: "SiliconFlow",
  xiaomi: "MiMo",
};

type SortMode = "name" | "price" | "quality" | "popular" | "free";

function isFreeModel(m: ModelInfo): boolean {
  return m.pricing.prompt === 0 && m.pricing.completion === 0;
}

function isLegacyFreeRouterModel(m: ModelInfo): boolean {
  const normalizedName = m.name.trim().toLowerCase();
  return m.id === "openrouter/auto" || normalizedName === "free models router";
}

/** Sort modes with arena data (OpenRouter / OpenYak account) */
const SORT_BUTTONS_FULL: { key: SortMode; i18n: string }[] = [
  { key: "popular", i18n: "popular" },
  { key: "quality", i18n: "quality" },
  { key: "price", i18n: "price" },
  { key: "free", i18n: "free" },
  { key: "name", i18n: "name" },
];

/** Sort modes without arena data (direct API keys) */
const SORT_BUTTONS_SIMPLE: { key: SortMode; i18n: string }[] = [
  { key: "name", i18n: "name" },
  { key: "price", i18n: "price" },
];

/** Providers that have arena ranking data */
const ARENA_PROVIDERS = new Set<string | null>(["openyak"]);

export function ModelSelector() {
  const { t } = useTranslation("common");
  const [open, setOpen] = useState(false);
  const { data: models, isLoading, activeProvider } = useProviderModels();
  const hasArena = ARENA_PROVIDERS.has(activeProvider);
  const [sortBy, setSortBy] = useState<SortMode>(hasArena ? "popular" : "name");
  const { selectedModel, selectedProviderId, setSelectedModel } = useSettingsStore();
  const { isConnected, user } = useAuthStore();
  const arenaMap = useModelArenaMap(models);
  const sortButtons = hasArena ? SORT_BUTTONS_FULL : SORT_BUTTONS_SIMPLE;
  // Reset sort mode when switching between providers with/without arena data
  useEffect(() => { setSortBy(hasArena ? "popular" : "name"); }, [hasArena]);

  // Ollama warmup — fire-and-forget, deduplicate
  const warmedModelsRef = useRef<Set<string>>(new Set());
  const warmupOllamaModel = useCallback((modelId: string) => {
    if (activeProvider !== "ollama") return;
    const bare = modelId.replace(/^ollama\//, "");
    if (warmedModelsRef.current.has(bare)) return;
    warmedModelsRef.current.add(bare);
    api.post(API.OLLAMA.WARMUP, { model: bare }).catch(() => {});
  }, [activeProvider]);
  const visibleModels = useMemo(
    () => (models ?? []).filter((m) => !isLegacyFreeRouterModel(m)),
    [models],
  );

  const hasCredits = !!(isConnected && user && user.billing_mode === "credits" && user.credit_balance > 0);

  // Auto-select a sensible default when no model is selected or current model doesn't exist in the active provider
  useEffect(() => {
    if (visibleModels.length === 0) {
      // All models gone (e.g. deleted) — clear stale selection
      if (selectedModel) setSelectedModel(null);
      return;
    }
    const modelExists = selectedModel && visibleModels.some((m) => m.id === selectedModel && m.provider_id === selectedProviderId);
    if (!modelExists) {
      let chosen: ModelInfo;
      if (activeProvider === "openyak" || activeProvider === "byok") {
        const preferred = visibleModels.find((m) => m.id === "openyak/best-free");
        const fallback = visibleModels.find((m) => isFreeModel(m));
        chosen = preferred ?? fallback ?? visibleModels[0];
      } else {
        chosen = visibleModels[0];
      }
      setSelectedModel(chosen.id, chosen.provider_id);
      warmupOllamaModel(chosen.id);
    }
  }, [visibleModels, selectedModel, selectedProviderId, setSelectedModel, activeProvider, warmupOllamaModel]);

  const { pinnedModel, freeModels, paidModels } = useMemo(() => {
    if (visibleModels.length === 0) return { pinnedModel: null, freeModels: [], paidModels: [] };

    let pinned: ModelInfo | null = null;
    const free: ModelInfo[] = [];
    const paid: ModelInfo[] = [];

    for (const m of visibleModels) {
      if (m.id === "openyak/best-free") pinned = m;
      else if (isFreeModel(m)) free.push(m);
      else paid.push(m);
    }

    const sortFn = (a: ModelInfo, b: ModelInfo) => {
      if (sortBy === "price") return a.pricing.prompt - b.pricing.prompt;
      if (sortBy === "quality") {
        const sa = arenaMap.get(a.id)?.arenaScore ?? 0;
        const sb = arenaMap.get(b.id)?.arenaScore ?? 0;
        if (sa === 0 && sb === 0) return a.name.localeCompare(b.name);
        if (sa === 0) return 1;
        if (sb === 0) return -1;
        if (sa !== sb) return sb - sa;
        return a.name.localeCompare(b.name);
      }
      if (sortBy === "popular") {
        const va = arenaMap.get(a.id)?.popularityRank ?? 0;
        const vb = arenaMap.get(b.id)?.popularityRank ?? 0;
        if (va === 0 && vb === 0) return a.name.localeCompare(b.name);
        if (va === 0) return 1;
        if (vb === 0) return -1;
        if (va !== vb) return va - vb;
        return a.name.localeCompare(b.name);
      }
      // Name sort: reverse natural order so higher version numbers come first
      // e.g. "GPT-5" before "GPT-4", "Claude Sonnet 4.6" before "Claude Sonnet 4"
      return b.name.localeCompare(a.name, undefined, { numeric: true });
    };

    free.sort(sortFn);
    paid.sort(sortFn);

    return { pinnedModel: pinned, freeModels: free, paidModels: paid };
  }, [visibleModels, sortBy, arenaMap]);

  const selectedInfo = visibleModels.find((m) => m.id === selectedModel && m.provider_id === selectedProviderId)
    ?? visibleModels.find((m) => m.id === selectedModel);
  const displayName = selectedInfo?.name ?? "Auto-select";

  if (isLoading || !models) {
    return (
      <div className="px-3 py-2">
        <div className="h-9 rounded-md bg-[var(--surface-tertiary)] animate-pulse" />
      </div>
    );
  }

  return (
    <div className="px-3 py-1">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="flex h-8 w-full items-center justify-between rounded-md border border-[var(--border-default)] bg-transparent px-3 text-xs text-[var(--text-primary)] hover:bg-[var(--surface-secondary)] transition-colors focus:outline-none"
          >
            <span className="truncate">{displayName}</span>
            <ChevronDown className="h-3.5 w-3.5 opacity-50 shrink-0" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-[360px] p-0 overflow-hidden" align="start" sideOffset={4}>
          <TooltipProvider delayDuration={300}>
            <Command>
              <CommandInput placeholder={t("searchModels")} />
              {/* Sort bar */}
              <div className="flex items-center gap-1 px-3 py-1.5 border-b border-[var(--border-default)]">
                <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mr-auto">
                  {t("sortBy")}
                </span>
                {sortButtons.map(({ key, i18n }) => (
                  <button
                    key={key}
                    type="button"
                    onPointerDown={(e) => e.preventDefault()}
                    onClick={() => setSortBy(key)}
                    className={cn(
                      "px-2 py-0.5 text-[11px] rounded-md transition-colors",
                      sortBy === key
                        ? "bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                        : "text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]",
                    )}
                  >
                    {t(i18n)}
                  </button>
                ))}
              </div>
              <CommandList>
                <CommandEmpty>{t("noModelFound")}</CommandEmpty>

                {/* Pinned platform model at top */}
                {pinnedModel && (
                  <CommandGroup>
                    <CommandItem
                      value={pinnedModel.name}
                      onSelect={() => {
                        setSelectedModel(pinnedModel.id, pinnedModel.provider_id);
                        warmupOllamaModel(pinnedModel.id);
                        setOpen(false);
                      }}
                      className="text-sm"
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4 shrink-0",
                          selectedModel === pinnedModel.id && selectedProviderId === pinnedModel.provider_id ? "opacity-100" : "opacity-0",
                        )}
                      />
                      <Star className="mr-1.5 h-3.5 w-3.5 shrink-0 text-[var(--text-tertiary)] fill-[var(--text-tertiary)]" />
                      <span className="truncate flex-1 font-medium">{pinnedModel.name}</span>
                      <span className="ml-2 shrink-0 text-[10px] font-medium text-[var(--color-success)] bg-[var(--color-success)]/10 px-1.5 py-0.5 rounded">
                        FREE
                      </span>
                    </CommandItem>
                  </CommandGroup>
                )}

                {/* Paid models first (hidden in free filter mode) */}
                {sortBy !== "free" && paidModels.length > 0 && (
                  <CommandGroup heading={freeModels.length > 0 ? t("premium") : undefined}>
                    {paidModels.map((model) => (
                      <ModelRow
                        key={`${model.provider_id}/${model.id}`}
                        model={model}
                        isSelected={selectedModel === model.id && selectedProviderId === model.provider_id}
                        arena={arenaMap.get(model.id)}
                        sortBy={sortBy}
                        hasCredits={hasCredits}
                        onSelect={() => {
                          setSelectedModel(model.id, model.provider_id);
                          warmupOllamaModel(model.id);
                          setOpen(false);
                        }}
                        t={t}
                      />
                    ))}
                  </CommandGroup>
                )}

                {/* Free models below */}
                {freeModels.length > 0 && (
                  <CommandGroup heading={t("free")}>
                    {freeModels.map((model) => (
                      <ModelRow
                        key={`${model.provider_id}/${model.id}`}
                        model={model}
                        isSelected={selectedModel === model.id && selectedProviderId === model.provider_id}
                        arena={arenaMap.get(model.id)}
                        sortBy={sortBy}
                        hasCredits={hasCredits}
                        onSelect={() => {
                          setSelectedModel(model.id, model.provider_id);
                          warmupOllamaModel(model.id);
                          setOpen(false);
                        }}
                        t={t}
                      />
                    ))}
                  </CommandGroup>
                )}
              </CommandList>
            </Command>
          </TooltipProvider>
        </PopoverContent>
      </Popover>
    </div>
  );
}

function ModelRow({
  model,
  isSelected,
  arena,
  sortBy,
  hasCredits,
  onSelect,
  t,
}: {
  model: ModelInfo;
  isSelected: boolean;
  arena: ArenaScore | undefined;
  sortBy: SortMode;
  hasCredits: boolean;
  onSelect: () => void;
  t: (key: string) => string;
}) {
  const free = isFreeModel(model);
  const isSubscription = model.provider_id === "openai-subscription";
  const inputCredits = usdToCreditsPerM(model.pricing.prompt);
  const outputCredits = usdToCreditsPerM(model.pricing.completion);

  const showArena =
    (sortBy === "quality" && arena && arena.arenaScore > 0) ||
    (sortBy === "popular" && arena && arena.popularityRank > 0);

  // Provider label for disambiguation (only shown when provider_id differs from common aggregator)
  const providerLabel = PROVIDER_LABELS[model.provider_id] ?? model.provider_id;
  const showProviderBadge = model.provider_id !== "openrouter" && model.provider_id !== "openai-subscription" && model.provider_id !== "ollama";

  return (
    <CommandItem
      value={`${model.name} ${providerLabel}`}
      onSelect={onSelect}
      className="text-sm"
    >
      <Check
        className={cn(
          "mr-2 h-4 w-4 shrink-0",
          isSelected ? "opacity-100" : "opacity-0",
        )}
      />
      <span className="truncate flex-1">{model.name}</span>
      {showProviderBadge && (
        <span className="ml-1.5 shrink-0 text-[9px] font-medium text-[var(--text-tertiary)] bg-[var(--surface-tertiary)] px-1 py-0.5 rounded">
          {providerLabel}
        </span>
      )}
      {isSubscription ? (
        <span className="ml-2 shrink-0 text-[10px] font-medium text-[var(--brand-primary)] bg-[var(--brand-primary)]/10 px-1.5 py-0.5 rounded">
          INCLUDED
        </span>
      ) : free ? (
        <span className="ml-2 shrink-0 text-[10px] font-medium text-[var(--color-success)] bg-[var(--color-success)]/10 px-1.5 py-0.5 rounded">
          FREE
        </span>
      ) : (
        <>
          {showArena && arena ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="ml-2 shrink-0 text-[11px] font-mono tabular-nums text-[var(--text-tertiary)]">
                  {sortBy === "quality" ? arena.arenaScore : `#${arena.popularityRank}`}
                </span>
              </TooltipTrigger>
              <TooltipContent side="right" className="text-xs">
                {arena.arenaScore > 0 && <div>Intelligence: {arena.arenaScore}</div>}
                {arena.popularityRank > 0 && <div>Popularity: #{arena.popularityRank}</div>}
                <div>{t("inputPrice")}: {formatCreditsPerM(inputCredits)}</div>
                <div>{t("outputPrice")}: {formatCreditsPerM(outputCredits)}</div>
              </TooltipContent>
            </Tooltip>
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="ml-2 shrink-0 text-[11px] font-mono tabular-nums text-[var(--text-tertiary)]">
                  {formatCreditsPerM(inputCredits)}
                </span>
              </TooltipTrigger>
              <TooltipContent side="right" className="text-xs">
                <div>{t("inputPrice")}: {formatCreditsPerM(inputCredits)}</div>
                <div>{t("outputPrice")}: {formatCreditsPerM(outputCredits)}</div>
                {arena && arena.arenaScore > 0 && <div>Intelligence: {arena.arenaScore}</div>}
                {arena && arena.popularityRank > 0 && <div>Popularity: #{arena.popularityRank}</div>}
              </TooltipContent>
            </Tooltip>
          )}
          {!hasCredits && (
            <Lock className="ml-1 h-3 w-3 shrink-0 text-[var(--text-tertiary)]" />
          )}
        </>
      )}
    </CommandItem>
  );
}

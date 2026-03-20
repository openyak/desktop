"use client";

import { useMemo } from "react";
import { useModels } from "@/hooks/use-models";
import { useSettingsStore } from "@/stores/settings-store";
import type { ActiveProvider } from "@/stores/settings-store";

const PROVIDER_ID_MAP: Record<NonNullable<ActiveProvider>, string> = {
  openyak: "openrouter",
  byok: "openrouter",
  chatgpt: "openai-subscription",
};

export function useProviderModels() {
  const { data: allModels, isLoading } = useModels();
  const activeProvider = useSettingsStore((s) => s.activeProvider);

  const data = useMemo(() => {
    if (!allModels) return [];
    // No provider selected → return empty (NOT all models).
    // This prevents the model dropdown from showing mixed models during loading.
    if (!activeProvider) return [];
    const providerId = PROVIDER_ID_MAP[activeProvider];
    return allModels.filter((m) => m.provider_id === providerId);
  }, [allModels, activeProvider]);

  return { data, allModels, isLoading, activeProvider };
}

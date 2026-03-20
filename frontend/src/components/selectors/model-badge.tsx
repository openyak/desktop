"use client";

import { Badge } from "@/components/ui/badge";
import { useSettingsStore } from "@/stores/settings-store";

export function ModelBadge() {
  const model = useSettingsStore((s) => s.selectedModel);

  if (!model) return null;

  // Extract short model name (e.g. "z-ai/glm-4.7-flash" → "glm-4.7-flash")
  const shortName = model.includes("/") ? model.split("/").pop() : model;

  return (
    <Badge variant="outline" className="text-[10px] px-2 py-0 max-w-[160px] truncate">
      {shortName}
    </Badge>
  );
}

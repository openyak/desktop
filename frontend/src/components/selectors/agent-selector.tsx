"use client";

import { useTranslation } from "react-i18next";
import { useAgents } from "@/hooks/use-agents";
import { useSettingsStore } from "@/stores/settings-store";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function AgentSelector() {
  const { t } = useTranslation("settings");
  const { data: agents, isLoading } = useAgents();
  const { selectedAgent, setSelectedAgent } = useSettingsStore();

  // Only show primary agents
  const primaryAgents = agents?.filter((a) => a.mode === "primary") ?? [];
  const selectedAgentLabel = primaryAgents.find((a) => a.name === selectedAgent)?.name ?? selectedAgent;

  if (isLoading) {
    return (
      <div className="px-3 py-2">
        <div className="h-9 rounded-md bg-[var(--surface-tertiary)] animate-pulse" />
      </div>
    );
  }

  return (
    <div className="px-3 py-1">
      <label className="text-[10px] text-[var(--text-tertiary)] uppercase font-semibold tracking-wider mb-1 block">
        {t("agentLabel")}
      </label>
      <Select value={selectedAgent} onValueChange={setSelectedAgent}>
        <SelectTrigger className="h-8 text-xs">
          <SelectValue className="truncate">{selectedAgentLabel}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          {primaryAgents.map((agent) => (
            <SelectItem key={agent.name} value={agent.name} className="text-xs">
              <div className="min-w-0">
                <div className="font-medium text-[var(--text-primary)] flex items-center gap-1.5">
                  {agent.name}
                  {Boolean(agent.metadata?.custom) && (
                    <span className="text-[9px] px-1 py-0.5 rounded bg-[var(--surface-tertiary)] text-[var(--text-tertiary)] leading-none">
                      {t("agentCustom")}
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-[var(--text-tertiary)] truncate" title={agent.description}>
                  {t(`agentDesc_${agent.name}`, { defaultValue: agent.description })}
                </div>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

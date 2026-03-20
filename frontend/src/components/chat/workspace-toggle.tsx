"use client";

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { FolderOpen, X } from "lucide-react";
import { Loader2 } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { useSettingsStore } from "@/stores/settings-store";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import { browseDirectory } from "@/lib/upload";
import { cn } from "@/lib/utils";

interface WorkspaceToggleProps {
  /** When provided, workspace changes are persisted to this session via PATCH. */
  sessionId?: string;
  /** The session's current directory (used when sessionId is provided). */
  directory?: string | null;
  /** Whether the workspace is currently being indexed. Shows spinner when true. */
  isIndexing?: boolean;
}

function getDisplayName(path: string | null | undefined): string | null {
  if (!path || path === ".") return null;
  const normalized = path.replace(/\\/g, "/").replace(/\/$/, "");
  const parts = normalized.split("/");
  return parts[parts.length - 1] || null;
}

export function WorkspaceToggle({ sessionId, directory, isIndexing }: WorkspaceToggleProps) {
  const { t } = useTranslation("chat");
  const queryClient = useQueryClient();
  const [popoverOpen, setPopoverOpen] = useState(false);

  // For new chats (no sessionId), use global settings store
  const globalWorkspace = useSettingsStore((s) => s.workspaceDirectory);
  const setGlobalWorkspace = useSettingsStore((s) => s.setWorkspaceDirectory);

  // Resolved values depending on context
  const currentPath = sessionId ? directory : globalWorkspace;
  const displayName = getDisplayName(currentPath);

  const handleBrowse = useCallback(async () => {
    try {
      const path = await browseDirectory(t("workspaceSet"));
      if (path) {
        if (sessionId) {
          // Persist to the current session only — don't pollute the global default
          await api.patch(API.SESSIONS.DETAIL(sessionId), { directory: path });
          queryClient.invalidateQueries({ queryKey: queryKeys.sessions.detail(sessionId) });
          queryClient.invalidateQueries({ queryKey: queryKeys.sessions.all });
        } else {
          // New chat: update the global default (used until session is created)
          setGlobalWorkspace(path);
        }
        setPopoverOpen(false);
      }
    } catch (err) {
      console.error("Failed to browse directory:", err);
      toast.error("Failed to open folder picker");
    }
  }, [sessionId, t, queryClient, setGlobalWorkspace]);

  const handleClear = useCallback(async () => {
    if (sessionId) {
      await api.patch(API.SESSIONS.DETAIL(sessionId), { directory: "." });
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions.detail(sessionId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions.all });
    } else {
      setGlobalWorkspace(null);
    }
    setPopoverOpen(false);
  }, [sessionId, queryClient, setGlobalWorkspace]);

  return (
    <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[13px] transition-colors max-w-[200px]",
            displayName
              ? "bg-[var(--surface-tertiary)] text-[var(--text-primary)]"
              : "text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)]",
          )}
        >
          {isIndexing ? (
            <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
          ) : (
            <FolderOpen className="h-4 w-4 shrink-0" />
          )}
          <span className="truncate">{displayName || t("workspaceNone")}</span>
          {isIndexing && displayName && (
            <span className="text-[11px] text-[var(--text-tertiary)] shrink-0">Indexing…</span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80">
        <div className="space-y-3">
          <p className="text-sm font-medium text-[var(--text-primary)]">{t("workspace")}</p>
          <div className="rounded-lg bg-[var(--surface-secondary)] px-3 py-2 text-[13px] text-[var(--text-secondary)] break-all">
            {currentPath && currentPath !== "." ? currentPath : t("workspaceNone")}
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" className="flex-1" onClick={handleBrowse}>
              <FolderOpen className="h-3.5 w-3.5 mr-1.5" />
              {t("workspaceBrowse")}
            </Button>
            {displayName && (
              <Button type="button" variant="ghost" size="sm" onClick={handleClear}>
                <X className="h-3.5 w-3.5 mr-1.5" />
                {t("workspaceClear")}
              </Button>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

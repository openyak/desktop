"use client";

import { useEffect, useMemo } from "react";
import { useSessions } from "@/hooks/use-sessions";
import { IS_DESKTOP } from "@/lib/constants";
import { desktopAPI, type TrayRecent } from "@/lib/tauri-api";
import { useSidebarStore } from "@/stores/sidebar-store";

const TRAY_RECENT_LIMIT = 6;

/**
 * Keeps the desktop tray's Recent Chats list in sync with the sidebar's
 * sessions query, and routes the tray's "Search Chats…" item to the
 * command palette. Web mode is a no-op.
 */
export function useTraySync() {
  const { data: sessionPages } = useSessions();
  const setSearchModalOpen = useSidebarStore((s) => s.setSearchModalOpen);

  const recents = useMemo<TrayRecent[]>(() => {
    if (!IS_DESKTOP) return [];
    const all = sessionPages?.pages.flat() ?? [];
    return all
      .filter((s) => !s.time_archived)
      .slice(0, TRAY_RECENT_LIMIT)
      .map((s) => ({ id: s.id, title: s.title ?? null }));
  }, [sessionPages]);

  const fingerprint = useMemo(
    () => recents.map((r) => `${r.id}:${r.title ?? ""}`).join("|"),
    [recents],
  );

  useEffect(() => {
    if (!IS_DESKTOP) return;
    desktopAPI.updateTrayRecents(recents).catch(() => {
      // Tray may not be ready yet on first boot; the next session-list tick
      // will retry. Silent failure is fine.
    });
  }, [fingerprint, recents]);

  useEffect(() => {
    if (!IS_DESKTOP) return;
    return desktopAPI.onOpenSearch(() => setSearchModalOpen(true));
  }, [setSearchModalOpen]);
}

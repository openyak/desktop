"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";

export type IndexingStatus = "unavailable" | "not_indexed" | "indexing" | "indexed" | "error";

interface IndexStatusResponse {
  workspace: string;
  session_id?: string | null;
  status: string;
  error?: string | null;
}

/**
 * Poll FTS indexing status for a session's workspace index.
 * On first call for a new session+workspace, triggers indexing via POST.
 * Returns isIndexing=true while indexing is in progress.
 */
export function useIndexStatus(workspace: string | null | undefined, sessionId?: string | null) {
  const triggeredRef = useRef<Set<string>>(new Set());

  const enabled = !!workspace && workspace !== "." && !!sessionId;
  const triggerKey = sessionId ? `${workspace}::${sessionId}` : "";

  // Trigger indexing once per session+workspace
  useEffect(() => {
    if (!enabled || !sessionId || triggeredRef.current.has(triggerKey)) return;
    triggeredRef.current.add(triggerKey);

    api.post(API.FTS.INDEX(workspace!, sessionId)).catch(() => {
      // FTS disabled or backend error — silently ignore
    });
  }, [workspace, sessionId, enabled, triggerKey]);

  const { data } = useQuery<IndexStatusResponse>({
    queryKey: queryKeys.indexStatus(triggerKey),
    queryFn: async () => {
      try {
        return await api.get<IndexStatusResponse>(API.FTS.INDEX(workspace!, sessionId!));
      } catch {
        return { workspace: workspace!, status: "unavailable" };
      }
    },
    enabled,
    staleTime: 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || status === "indexing" || status === "not_indexed") return 1000;
      return false;
    },
  });

  const status = (data?.status ?? (enabled ? "not_indexed" : "unavailable")) as IndexingStatus;
  const isIndexing = enabled && (status === "indexing" || status === "not_indexed");

  return { status, isIndexing };
}

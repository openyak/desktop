"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/constants";
import type { McpStatusResponse } from "@/types/mcp";

const MCP_QUERY_KEY = ["mcp-status"] as const;

export function useMcpStatus() {
  return useQuery({
    queryKey: MCP_QUERY_KEY,
    queryFn: () => api.get<McpStatusResponse>(API.MCP.STATUS),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useMcpReconnect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.post<{ success: boolean; servers: McpStatusResponse["servers"] }>(
        API.MCP.RECONNECT(name),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MCP_QUERY_KEY });
    },
  });
}

export function useMcpAuthStart() {
  return useMutation({
    mutationFn: (name: string) =>
      api.post<{ success: boolean; auth_url?: string; state?: string; error?: string }>(
        API.MCP.AUTH_START(name),
      ),
  });
}

export function useMcpDisconnect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.post<{ success: boolean; servers: McpStatusResponse["servers"] }>(
        API.MCP.DISCONNECT(name),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MCP_QUERY_KEY });
    },
  });
}

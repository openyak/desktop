"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import type { AgentInfo } from "@/types/agent";

export function useAgents() {
  return useQuery({
    queryKey: queryKeys.agents,
    queryFn: () => api.get<AgentInfo[]>(API.AGENTS),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import type { UsageStats } from "@/types/usage";

export function useUsage(days: number = 30) {
  return useQuery({
    queryKey: queryKeys.usage(days),
    queryFn: () => api.get<UsageStats>(`${API.USAGE}?days=${days}`),
    staleTime: 60 * 1000,
  });
}

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import type { PluginsStatusResponse, PluginDetail, SkillInfo } from "@/types/plugins";

export function usePluginsStatus() {
  return useQuery({
    queryKey: queryKeys.plugins.all,
    queryFn: () => api.get<PluginsStatusResponse>(API.PLUGINS.STATUS),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function usePluginDetail(name: string | null) {
  return useQuery({
    queryKey: queryKeys.plugins.detail(name ?? ""),
    queryFn: () => api.get<PluginDetail>(API.PLUGINS.DETAIL(name!)),
    enabled: !!name,
    staleTime: 60_000,
  });
}

export function useSkills() {
  return useQuery({
    queryKey: queryKeys.skills,
    queryFn: () => api.get<SkillInfo[]>(API.SKILLS),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function usePluginToggle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, enable }: { name: string; enable: boolean }) =>
      api.post<{ success: boolean; plugins: PluginsStatusResponse["plugins"] }>(
        enable ? API.PLUGINS.ENABLE(name) : API.PLUGINS.DISABLE(name),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.plugins.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.skills });
    },
  });
}

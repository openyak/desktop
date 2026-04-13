"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import type { ChannelsResponse, ChannelSystemStatus } from "@/types/channels";

export function useChannels() {
  return useQuery({
    queryKey: queryKeys.channels,
    queryFn: () => api.get<ChannelsResponse>(API.CHANNELS.LIST),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useChannelStatus() {
  return useQuery({
    queryKey: queryKeys.channelStatus,
    queryFn: () => api.get<ChannelSystemStatus>(API.CHANNELS.STATUS),
    refetchInterval: 10_000,
  });
}

export function useAddChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, string>) =>
      api.post<{ ok: boolean; message: string }>(API.CHANNELS.ADD, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels });
      qc.invalidateQueries({ queryKey: queryKeys.channelStatus });
    },
  });
}

export function useRemoveChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { channel: string; account?: string }) =>
      api.post<{ ok: boolean; message: string }>(API.CHANNELS.REMOVE, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels });
      qc.invalidateQueries({ queryKey: queryKeys.channelStatus });
    },
  });
}

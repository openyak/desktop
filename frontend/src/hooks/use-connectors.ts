"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import type { ConnectorsResponse } from "@/types/connectors";

function errorDetail(error: unknown, fallback: string) {
  if (
    typeof error === "object" &&
    error &&
    "body" in error &&
    typeof (error as { body?: unknown }).body === "object" &&
    (error as { body?: Record<string, unknown> }).body
  ) {
    const detail = (error as { body?: Record<string, unknown> }).body?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  if (error instanceof Error) return error.message || fallback;
  return fallback;
}

export function useConnectors() {
  return useQuery({
    queryKey: queryKeys.connectors,
    queryFn: () => api.get<ConnectorsResponse>(API.CONNECTORS.LIST),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useConnectorToggle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enable }: { id: string; enable: boolean }) =>
      api.post<{ success: boolean }>(
        enable ? API.CONNECTORS.ENABLE(id) : API.CONNECTORS.DISABLE(id),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.connectors });
    },
  });
}

export function useConnectorConnect() {
  return useMutation({
    mutationFn: (id: string) =>
      api.post<{ success: boolean; auth_url?: string; state?: string; error?: string }>(
        API.CONNECTORS.CONNECT(id),
      ),
    onError: (error) => {
      toast.error(errorDetail(error, "Failed to connect connector"));
    },
  });
}

export function useConnectorDisconnect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.post<{ success: boolean }>(API.CONNECTORS.DISCONNECT(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.connectors });
    },
  });
}

export function useConnectorReconnect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.post<{ success: boolean }>(API.CONNECTORS.RECONNECT(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.connectors });
    },
    onError: (error) => {
      toast.error(errorDetail(error, "Failed to reconnect connector"));
    },
  });
}

export function useSetConnectorToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, token }: { id: string; token: string }) =>
      api.post<{ success: boolean }>(API.CONNECTORS.SET_TOKEN(id), { token }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.connectors });
    },
    onError: (error) => {
      toast.error(errorDetail(error, "Failed to save connector token"));
    },
  });
}

export function useAddCustomConnector() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { id: string; name: string; url: string; description?: string; category?: string }) =>
      api.post<{ success: boolean }>(API.CONNECTORS.ADD, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.connectors });
    },
  });
}

export function useRemoveConnector() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<{ success: boolean }>(API.CONNECTORS.REMOVE(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.connectors });
    },
  });
}

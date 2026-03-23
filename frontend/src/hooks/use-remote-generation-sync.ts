"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import { useChatStore } from "@/stores/chat-store";

/**
 * Poll for active generations in the current session.
 *
 * When mobile (or another client) starts a generation in a session that the PC
 * is currently viewing, the PC has no way to discover the stream_id — it only
 * sets streamId when *it* initiates a prompt.
 *
 * This hook polls `GET /api/chat/active` every few seconds. When it finds an
 * active generation for the current session that isn't already tracked locally,
 * it sets the chatStore's streamId so `useSSE` activates and streams events.
 */
const POLL_INTERVAL = 5_000; // 5 seconds

export function useRemoteGenerationSync(sessionId: string | undefined) {
  const queryClient = useQueryClient();
  const knownStreamIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    let active = true;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      if (!active) return;

      try {
        const jobs = await api.get<{ stream_id: string; session_id: string }[]>(
          API.CHAT.ACTIVE,
        );

        if (!active) return;

        const match = jobs.find((j) => j.session_id === sessionId);
        const chatState = useChatStore.getState();

        if (match) {
          // Skip if the PC is already tracking this exact stream (local generation)
          if (chatState.streamId === match.stream_id) {
            knownStreamIdRef.current = match.stream_id;
          } else if (knownStreamIdRef.current !== match.stream_id) {
            // New remote generation discovered — activate streaming
            knownStreamIdRef.current = match.stream_id;

            // Refetch messages to show the new user message that mobile sent
            await queryClient.invalidateQueries({
              queryKey: queryKeys.messages.list(sessionId),
            });

            // Activate streaming — this triggers useSSE to connect
            chatState.startGeneration(match.stream_id, sessionId);
          }
        } else {
          // No active generation — if we were tracking one from a remote client,
          // it has finished. Refetch messages to get the final state.
          if (knownStreamIdRef.current) {
            knownStreamIdRef.current = null;
            // Only refetch if we're not in the middle of a local generation
            if (!chatState.isGenerating) {
              queryClient.invalidateQueries({
                queryKey: queryKeys.messages.list(sessionId),
              });
            }
          }
        }
      } catch {
        // Silently ignore polling errors
      }

      if (active) {
        timer = setTimeout(poll, POLL_INTERVAL);
      }
    };

    // Start polling
    poll();

    return () => {
      active = false;
      knownStreamIdRef.current = null;
      if (timer) clearTimeout(timer);
    };
  }, [sessionId, queryClient]);
}

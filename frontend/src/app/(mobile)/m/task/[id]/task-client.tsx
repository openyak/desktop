"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChatView } from "@/components/chat/chat-view";
import { isRemoteMode } from "@/lib/remote-connection";
import { useChatStore } from "@/stores/chat-store";

function TaskClientInner({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (!isRemoteMode()) {
      router.replace("/m/settings");
    }
  }, [router]);

  const resolvedId = sessionId === "_"
    ? searchParams.get("sessionId") ?? ""
    : sessionId;

  // If navigated with a stream_id (e.g., from new task page), seed the
  // chatStore immediately so useSSE activates without waiting for the poll.
  const streamIdParam = searchParams.get("stream_id");
  useEffect(() => {
    if (resolvedId && streamIdParam) {
      const chatState = useChatStore.getState();
      if (!chatState.isGenerating || chatState.streamId !== streamIdParam) {
        chatState.startGeneration(streamIdParam, resolvedId);
      }
    }
  }, [resolvedId, streamIdParam]);

  if (!resolvedId) return null;

  // No custom header — ChatHeader inside ChatView handles everything.
  // In remote mode, ChatHeader shows back button instead of sidebar toggle.
  return (
    <div className="flex flex-col h-dvh pt-[env(safe-area-inset-top)]">
      <ChatView sessionId={resolvedId} />
    </div>
  );
}

export function MobileTaskClient({ sessionId }: { sessionId: string }) {
  return (
    <Suspense fallback={null}>
      <TaskClientInner sessionId={sessionId} />
    </Suspense>
  );
}

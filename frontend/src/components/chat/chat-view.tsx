"use client";

import { useCallback, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { useChat } from "@/hooks/use-chat";
import { useMessages } from "@/hooks/use-messages";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { useArtifactStore } from "@/stores/artifact-store";
import { useActivityStore } from "@/stores/activity-store";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import { ChatHeader } from "./chat-header";
import { ChatForm } from "./chat-form";
import { MessageList } from "@/components/messages/message-list";
import { PermissionDialog } from "@/components/interactive/permission-dialog";
import { QuestionPrompt } from "@/components/interactive/question-prompt";
import { PlanAcceptPrompt } from "@/components/interactive/plan-accept-prompt";
import { OfflineOverlay } from "@/components/layout/offline-overlay";
import type { SessionResponse } from "@/types/session";

interface ChatViewProps {
  sessionId: string;
}

export function ChatView({ sessionId }: ChatViewProps) {
  const {
    sendMessage,
    editAndResend,
    stopGeneration,
    respondToPermission,
    respondToQuestion,
    respondToPlanReview,
    isGenerating,
    streamId,
    pendingUserText,
    pendingAttachments,
    streamingParts,
    streamingText,
    streamingReasoning,
    pendingPermission,
    pendingQuestion,
    pendingPlanReview,
  } = useChat(sessionId);

  const { messages, isLoading, hasPreviousPage, isFetchingPreviousPage, fetchPreviousPage } = useMessages(sessionId);

  const { data: session } = useQuery({
    queryKey: queryKeys.sessions.detail(sessionId),
    queryFn: () => api.get<SessionResponse>(API.SESSIONS.DETAIL(sessionId)),
    staleTime: 30_000,
  });

  // Close right-side panels when switching sessions
  useEffect(() => {
    useArtifactStore.getState().clearAll();
    useActivityStore.getState().close();
  }, [sessionId]);

  // Copy last assistant message to clipboard
  const handleCopyLast = useCallback(() => {
    if (!messages || messages.length === 0) return;

    // Find last assistant message
    const lastAssistantMessage = [...messages]
      .reverse()
      .find((msg) => (msg.data as { role: string }).role === "assistant");

    if (!lastAssistantMessage) {
      toast.error("No assistant message found");
      return;
    }

    // Extract text content
    const textContent = lastAssistantMessage.parts
      .filter((p) => p.data.type === "text")
      .map((p) => (p.data as { type: "text"; text: string }).text)
      .join("\n");

    if (!textContent) {
      toast.error("No text content to copy");
      return;
    }

    navigator.clipboard.writeText(textContent);
    toast.success("Copied to clipboard");
  }, [messages]);

  // Global keyboard shortcuts
  useKeyboardShortcuts({
    onStop: stopGeneration,
    onCopyLast: handleCopyLast,
  });

  return (
    <div className="relative flex flex-1 flex-col h-full overflow-hidden bg-[var(--surface-chat)]">
      <OfflineOverlay />
      <ChatHeader sessionId={sessionId} />

      {/* Message list */}
      <MessageList
        messages={messages}
        isLoading={isLoading}
        isGenerating={isGenerating}
        streamId={streamId}
        pendingUserText={pendingUserText}
        pendingAttachments={pendingAttachments}
        streamingParts={streamingParts}
        streamingText={streamingText}
        streamingReasoning={streamingReasoning}
        onEditAndResend={editAndResend}
        hasPreviousPage={hasPreviousPage}
        isFetchingPreviousPage={isFetchingPreviousPage}
        fetchPreviousPage={fetchPreviousPage}
      />

      {/* Interactive prompts */}
      {pendingPermission && (
        <PermissionDialog
          permission={pendingPermission}
          onRespond={respondToPermission}
        />
      )}

      {pendingQuestion && (
        <QuestionPrompt
          question={pendingQuestion}
          onRespond={respondToQuestion}
        />
      )}

      {/* Input — replaced by plan accept prompt when a plan review is pending */}
      {pendingPlanReview ? (
        <PlanAcceptPrompt onRespond={respondToPlanReview} />
      ) : (
        <ChatForm
          isGenerating={isGenerating}
          onSend={sendMessage}
          onStop={stopGeneration}
          sessionId={sessionId}
          directory={session?.directory}
        />
      )}
    </div>
  );
}

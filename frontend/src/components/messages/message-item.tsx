"use client";

import { memo } from "react";
import { UserMessage } from "./user-message";
import { AssistantMessage } from "./assistant-message";
import type { FileAttachment } from "@/types/chat";
import type { MessageResponse } from "@/types/message";

interface MessageItemProps {
  message: MessageResponse;
  onRegenerate?: () => void;
  onEditAndResend?: (messageId: string, newText: string, attachments?: FileAttachment[]) => Promise<boolean>;
  isGenerating?: boolean;
  /** Whether this message just arrived (animate) or was loaded from history (skip animation). */
  isNew?: boolean;
}

export const MessageItem = memo(function MessageItem({ message, onRegenerate, onEditAndResend, isGenerating, isNew = true }: MessageItemProps) {
  const role = (message.data as { role: string }).role;

  return (
    <div className="px-4 py-3">
      <div className="mx-auto max-w-3xl xl:max-w-4xl">
        {role === "user" ? (
          <UserMessage
            message={message}
            isNew={isNew}
            onEditAndResend={onEditAndResend}
            isGenerating={isGenerating}
          />
        ) : (
          <AssistantMessage message={message} onRegenerate={onRegenerate} isNew={isNew} />
        )}
      </div>
    </div>
  );
});

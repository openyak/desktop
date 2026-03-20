"use client";

import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface ChatTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  onSubmit?: () => void;
  /** When true, Enter / ArrowUp / ArrowDown are consumed by the mention popup */
  mentionActive?: boolean;
}

const ChatTextarea = forwardRef<HTMLTextAreaElement, ChatTextareaProps>(
  ({ className, onSubmit, onKeyDown, mentionActive, ...props }, ref) => {
    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // When the mention popup is open, let it handle navigation keys
      if (mentionActive) {
        if (
          e.key === "ArrowDown" ||
          e.key === "ArrowUp" ||
          e.key === "Enter" ||
          e.key === "Tab" ||
          e.key === "Escape"
        ) {
          // These are handled by FileMentionPopup's window keydown listener
          return;
        }
      }

      if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
        e.preventDefault();
        onSubmit?.();
      }
      onKeyDown?.(e);
    };

    return (
      <textarea
        ref={ref}
        rows={1}
        className={cn(
          "w-full resize-none bg-transparent text-[15px] leading-relaxed text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none overflow-y-auto scrollbar-none",
          className,
        )}
        onKeyDown={handleKeyDown}
        {...props}
      />
    );
  },
);
ChatTextarea.displayName = "ChatTextarea";

export { ChatTextarea };

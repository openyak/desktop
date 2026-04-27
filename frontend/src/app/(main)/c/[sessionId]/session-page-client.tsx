"use client";

import { ChatView } from "@/components/chat/chat-view";

interface SessionPageClientProps {
  sessionId: string | null;
}

export function SessionPageClient({ sessionId }: SessionPageClientProps) {
  if (!sessionId) return null;
  return <ChatView sessionId={sessionId} />;
}

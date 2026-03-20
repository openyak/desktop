"use client";

import { useSearchParams } from "next/navigation";
import { ChatView } from "@/components/chat/chat-view";
import { resolveSessionId } from "@/lib/routes";

export function SessionPageClient({ sessionId }: { sessionId: string }) {
  const searchParams = useSearchParams();
  const resolvedSessionId = resolveSessionId(sessionId, searchParams.get("sessionId"));

  if (!resolvedSessionId) return null;

  return <ChatView sessionId={resolvedSessionId} />;
}

"use client";

import { useParams, useSearchParams } from "next/navigation";
import { ChatView } from "@/components/chat/chat-view";
import { resolveSessionId } from "@/lib/routes";

interface SessionPageClientProps {
  sessionId?: string | null;
}

export function SessionPageClient({ sessionId: providedSessionId }: SessionPageClientProps = {}) {
  const params = useParams<{ sessionId?: string | string[] }>();
  const searchParams = useSearchParams();
  const routeSessionId = Array.isArray(params.sessionId)
    ? params.sessionId[0]
    : params.sessionId;
  const querySessionId = searchParams.get("sessionId");
  const sessionId = providedSessionId ?? resolveSessionId(routeSessionId ?? null, querySessionId);

  if (!sessionId) return null;
  return <ChatView sessionId={sessionId} />;
}

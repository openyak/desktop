"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChatView } from "@/components/chat/chat-view";
import { isRemoteMode } from "@/lib/remote-connection";

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

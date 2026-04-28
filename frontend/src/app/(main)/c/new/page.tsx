import { Suspense } from "react";
import { NewChatPageClient } from "./new-chat-page-client";

export default function NewChatPage() {
  return (
    <Suspense fallback={null}>
      <NewChatPageClient />
    </Suspense>
  );
}

"use client";

import { useSearchParams } from "next/navigation";
import { Landing } from "@/components/chat/landing";

export function NewChatPageClient() {
  const searchParams = useSearchParams();
  const directory = searchParams.get("directory");

  return <Landing directoryParam={directory ?? null} />;
}

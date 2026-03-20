"use client";

import { User } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { OpenYakLogo } from "@/components/ui/openyak-logo";

interface MessageAvatarProps {
  role: "user" | "assistant";
}

export function MessageAvatar({ role }: MessageAvatarProps) {
  if (role === "user") {
    return (
      <Avatar className="h-7 w-7">
        <AvatarFallback className="bg-[var(--surface-tertiary)]">
          <User className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
        </AvatarFallback>
      </Avatar>
    );
  }

  return (
    <Avatar className="h-7 w-7">
      <AvatarFallback className="bg-[var(--brand-primary)]">
        <OpenYakLogo size={14} className="text-[var(--brand-primary-text)]" />
      </AvatarFallback>
    </Avatar>
  );
}

"use client";

import { GitBranch } from "lucide-react";
import Link from "next/link";
import { getChatRoute } from "@/lib/routes";
import type { SubtaskPart as SubtaskPartType } from "@/types/message";

interface SubtaskPartProps {
  data: SubtaskPartType;
}

export function SubtaskPart({ data }: SubtaskPartProps) {
  return (
    <Link
      href={getChatRoute(data.session_id)}
      className="flex items-center gap-2 rounded-xl border border-[var(--border-default)] bg-[var(--surface-secondary)] px-3 py-2 text-xs hover:bg-[var(--surface-tertiary)] hover:shadow-[var(--shadow-sm)] transition-all duration-150"
    >
      <GitBranch className="h-3.5 w-3.5 text-[var(--brand-primary)] shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-[var(--text-primary)] truncate">{data.title}</p>
        {data.description && (
          <p className="text-[var(--text-tertiary)] truncate mt-0.5">{data.description}</p>
        )}
      </div>
    </Link>
  );
}

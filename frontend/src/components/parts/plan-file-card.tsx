"use client";

import { useCallback, useMemo } from "react";
import { ClipboardList, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { usePlanReviewStore } from "@/stores/plan-review-store";
import type { ToolPart } from "@/types/message";

interface PlanFileCardProps {
  data: ToolPart;
}

/**
 * Inline card for a submit_plan tool call — shows the plan title and file path.
 * Clicking opens the plan in the right review panel.
 * Follows the same structure as ArtifactCard.
 */
export function PlanFileCard({ data }: PlanFileCardProps) {
  const input = data.state.input as Record<string, unknown>;
  const metadata = (data.state.metadata ?? {}) as Record<string, unknown>;

  const title = (metadata.title ?? input.title ?? data.state.title ?? "Plan") as string;
  const plan = (metadata.plan ?? input.plan ?? "") as string;
  const planPath = (metadata.plan_path ?? "") as string;
  const metadataFiles = metadata.files_to_modify;
  const inputFiles = input.files_to_modify;
  const filesToModify = useMemo(
    () => (metadataFiles ?? inputFiles ?? []) as string[],
    [inputFiles, metadataFiles],
  );

  const isRunning = data.state.status === "running" || data.state.status === "pending";

  // Extract just the filename from the full path for display
  const displayPath = planPath ? planPath.replace(/\\/g, "/").split("/").slice(-2).join("/") : "";

  const handleClick = useCallback(() => {
    if (!plan) return;
    usePlanReviewStore.getState().openReview({
      callId: data.call_id,
      title,
      plan,
      filesToModify,
    });
  }, [data.call_id, title, plan, filesToModify]);

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={isRunning}
      className={cn(
        "flex items-center gap-3 w-full rounded-xl border px-4 py-3",
        "bg-[var(--surface-secondary)] hover:bg-[var(--surface-tertiary)]",
        "hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5 transition-all duration-150",
        "text-left group border-[var(--border-default)]",
        isRunning && "cursor-default",
      )}
    >
      {/* Icon */}
      <div className="flex items-center justify-center h-9 w-9 rounded-lg shrink-0 bg-[var(--surface-tertiary)]">
        {isRunning ? (
          <Loader2 className="h-4 w-4 text-[var(--text-tertiary)] animate-spin" />
        ) : (
          <ClipboardList className="h-4 w-4 text-[var(--brand-primary)]" />
        )}
      </div>

      {/* Title + path */}
      <div className="flex-1 min-w-0">
        <p className={cn(
          "text-sm font-medium text-[var(--text-primary)] truncate",
          isRunning && "shimmer-text",
        )}>
          {title}
        </p>
        {displayPath && (
          <p className="text-xs text-[var(--text-tertiary)] mt-0.5 font-mono truncate">
            {displayPath}
          </p>
        )}
      </div>
    </button>
  );
}

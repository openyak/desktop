"use client";

import { CheckCircle } from "lucide-react";
import type { StepStartPart, StepFinishPart } from "@/types/message";

interface StepIndicatorProps {
  type: "start" | "finish";
  data: StepStartPart | StepFinishPart;
}

export function StepIndicator({ type, data }: StepIndicatorProps) {
  if (type === "start") {
    const stepNum = (data as StepStartPart).snapshot?.step as number | undefined;
    return (
      <div className="flex items-center gap-2 py-2">
        <div className="h-1.5 w-1.5 rounded-full bg-[var(--brand-primary)]" />
        <span className="text-xs text-[var(--text-tertiary)] font-medium">
          {stepNum != null ? `Step ${String(stepNum)}` : "Step"}
        </span>
      </div>
    );
  }

  const finish = data as StepFinishPart;

  return (
    <div className="flex items-center gap-2 py-2">
      <CheckCircle className="h-3.5 w-3.5 text-[var(--tool-completed)]" />
      <span className="text-xs text-[var(--tool-completed)]">
        {finish.reason === "stop" ? "Complete" : finish.reason}
      </span>
    </div>
  );
}

"use client";

import { useCallback } from "react";
import { Wrench } from "lucide-react";
import { useArtifactStore } from "@/stores/artifact-store";

interface TryFixButtonProps {
  error: string;
  artifactType?: string;
  artifactTitle?: string;
}

/**
 * "Try fixing with Claude" button — sends error context to the chat input.
 * Used inside artifact renderers when a rendering error occurs.
 */
export function TryFixButton({ error, artifactType, artifactTitle }: TryFixButtonProps) {
  const requestFix = useArtifactStore((s) => s.requestFix);

  const handleClick = useCallback(() => {
    const parts: string[] = [];
    if (artifactTitle) {
      parts.push(`The ${artifactType || "artifact"} "${artifactTitle}" failed to render.`);
    } else {
      parts.push(`The ${artifactType || "artifact"} failed to render.`);
    }
    parts.push(`\nError:\n\`\`\`\n${error}\n\`\`\``);
    parts.push("\nPlease fix this error.");

    requestFix(parts.join(""));
  }, [error, artifactType, artifactTitle, requestFix]);

  return (
    <button
      type="button"
      onClick={handleClick}
      className="inline-flex items-center gap-1.5 mt-3 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--surface-tertiary)] hover:bg-[var(--surface-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-default)] transition-colors"
    >
      <Wrench className="h-3.5 w-3.5" />
      Try fixing with OpenYak
    </button>
  );
}

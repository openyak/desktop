"use client";

import { useEffect, useRef, useState } from "react";
import { useMermaid } from "@/hooks/use-mermaid";
import { cn } from "@/lib/utils";

interface MermaidBlockProps {
  code: string;
  className?: string;
}

export function MermaidBlock({ code, className }: MermaidBlockProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const { renderMermaid, isReady } = useMermaid();

  useEffect(() => {
    if (!isReady || !containerRef.current) return;

    const render = async () => {
      try {
        setError(null);
        const { svg } = await renderMermaid(code);
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to render diagram");
      }
    };

    render();
  }, [code, isReady, renderMermaid]);

  // Error state
  if (error) {
    return (
      <div className="rounded-lg border border-[var(--color-destructive)] bg-[var(--surface-secondary)] p-4 my-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium text-[var(--color-destructive)]">
            Mermaid Syntax Error
          </span>
        </div>
        <pre className="text-xs text-[var(--text-secondary)] overflow-x-auto whitespace-pre-wrap">
          {error}
        </pre>
        <details className="mt-2">
          <summary className="text-xs text-[var(--text-tertiary)] cursor-pointer hover:text-[var(--text-secondary)]">
            Show source code
          </summary>
          <pre className="mt-2 text-xs bg-[var(--surface-tertiary)] p-2 rounded overflow-x-auto border border-[var(--border-default)]">
            <code>{code}</code>
          </pre>
        </details>
      </div>
    );
  }

  // Loading state
  if (!isReady) {
    return (
      <div className="rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] p-8 my-3 text-center">
        <div className="text-sm text-[var(--text-secondary)]">Loading diagram...</div>
      </div>
    );
  }

  // Normal rendering
  return (
    <div
      ref={containerRef}
      className={cn(
        "mermaid-container rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] p-4 my-3 overflow-x-auto",
        className
      )}
    />
  );
}

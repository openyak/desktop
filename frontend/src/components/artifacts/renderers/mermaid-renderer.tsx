"use client";

import { useState, useEffect, useRef } from "react";
import { Code, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMermaid } from "@/hooks/use-mermaid";
import { TryFixButton } from "../try-fix-button";

interface MermaidRendererProps {
  content: string;
}

export function MermaidRenderer({ content }: MermaidRendererProps) {
  const [showSource, setShowSource] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { renderMermaid, isReady } = useMermaid();

  useEffect(() => {
    if (!isReady || !containerRef.current || showSource) return;

    const render = async () => {
      try {
        setError(null);
        const { svg } = await renderMermaid(content);
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to render diagram");
      }
    };

    render();
  }, [content, isReady, renderMermaid, showSource]);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-default)] bg-[var(--surface-tertiary)] shrink-0">
        <span className="text-[11px] font-medium text-[var(--text-secondary)] uppercase tracking-wide">
          {showSource ? "Source" : "Diagram"}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => setShowSource(!showSource)}
          title={showSource ? "Show diagram" : "Show source"}
        >
          {showSource ? <Eye className="h-3.5 w-3.5" /> : <Code className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {showSource ? (
          <pre className="text-[13px] leading-relaxed font-mono text-[var(--text-primary)]">
            {content}
          </pre>
        ) : error ? (
          <div className="text-sm text-[var(--color-destructive)] p-4">
            Diagram rendering error: {error}
            <TryFixButton error={error} artifactType="Mermaid diagram" />
          </div>
        ) : !isReady ? (
          <div className="flex items-center justify-center h-full text-sm text-[var(--text-tertiary)]">
            Loading diagram...
          </div>
        ) : (
          <div
            ref={containerRef}
            className="flex items-center justify-center min-h-full [&_svg]:max-w-full"
          />
        )}
      </div>
    </div>
  );
}

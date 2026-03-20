"use client";

import { useState, useCallback } from "react";
import { Copy, Check, WrapText } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CodeRendererProps {
  content: string;
  language?: string;
}

export function CodeRenderer({ content, language }: CodeRendererProps) {
  const [copied, setCopied] = useState(false);
  const [wrap, setWrap] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [content]);

  const lines = content.split("\n");

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-default)] bg-[var(--surface-tertiary)] shrink-0">
        <span className="text-[11px] font-medium text-[var(--text-secondary)] uppercase tracking-wide">
          {language || "code"}
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setWrap(!wrap)}
            title={wrap ? "No wrap" : "Wrap lines"}
          >
            <WrapText className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={handleCopy}
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>

      {/* Code area with line numbers */}
      <div className="flex-1 overflow-auto bg-[var(--surface-secondary)]">
        <div className="flex min-h-full">
          {/* Line numbers */}
          <div className="shrink-0 select-none border-r border-[var(--border-default)] bg-[var(--surface-tertiary)] px-3 py-3 text-right">
            {lines.map((_, i) => (
              <div key={i} className="text-[12px] leading-[1.6] font-mono text-[var(--text-tertiary)]">
                {i + 1}
              </div>
            ))}
          </div>
          {/* Code content */}
          <pre
            className={`flex-1 px-4 py-3 text-[13px] leading-[1.6] font-mono text-[var(--text-primary)] ${
              wrap ? "whitespace-pre-wrap break-all" : "overflow-x-auto"
            }`}
          >
            {content}
          </pre>
        </div>
      </div>
    </div>
  );
}

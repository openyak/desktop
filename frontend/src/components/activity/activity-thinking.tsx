"use client";

import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTranslation } from "react-i18next";
import { OpenYakLogo } from "@/components/ui/openyak-logo";

interface ActivityThinkingProps {
  texts: string[];
  duration?: number;
}

export function ActivityThinking({ texts, duration }: ActivityThinkingProps) {
  const { t } = useTranslation("chat");
  const combinedText = texts.filter(Boolean).join("\n\n---\n\n");

  const mdComponents = useMemo(
    () => ({
      code: ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => (
        <code
          className="rounded bg-[var(--surface-tertiary)] px-1 py-0.5 text-[0.85em] font-mono"
          {...props}
        >
          {children}
        </code>
      ),
    }),
    [],
  );

  if (!combinedText) return null;

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <OpenYakLogo size={16} className="text-[var(--text-secondary)]" />
        <h3 className="text-sm font-medium text-[var(--text-primary)]">
          {t("thinking")}
        </h3>
        {duration != null && (
          <span className="text-[10px] text-[var(--text-tertiary)] bg-[var(--surface-tertiary)] rounded-full px-2 py-0.5">
            {duration}s
          </span>
        )}
      </div>
      <div className="border-l-2 border-[var(--border-heavy)] pl-4 ml-1">
        <div className="prose prose-sm max-w-none text-[var(--text-secondary)] leading-relaxed [&_p]:my-2 [&_h1]:text-sm [&_h2]:text-sm [&_h3]:text-sm [&_strong]:text-[var(--text-primary)] [&_hr]:border-[var(--border-default)] [&_hr]:my-3">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {combinedText}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

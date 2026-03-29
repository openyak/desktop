"use client";

import { useMemo, useCallback, useState, memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Copy, Check, PanelRight, FileText, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { API } from "@/lib/constants";
import { useArtifactStore } from "@/stores/artifact-store";
import { classifyCodeBlock, isPreviewableFile, artifactTypeFromExtension, languageFromExtension, looksLikeFilePath } from "@/lib/artifacts";
import type { TextPart as TextPartType } from "@/types/message";
import type { Source } from "@/lib/sources";
import type { ArtifactType } from "@/types/artifact";
import { MermaidBlock } from "./mermaid-block";

interface TextPartProps {
  data: TextPartType;
  isStreaming?: boolean;
  sources?: Source[];
}

function CodeBlock({ className, children, ...props }: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || "");
  const lang = match?.[1] ?? "";
  const code = String(children).replace(/\n$/, "");
  const openArtifact = useArtifactStore((s) => s.openArtifact);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  // Classify code block as potential artifact
  const artifactType = classifyCodeBlock(lang, code);

  const handleOpenInPanel = useCallback(() => {
    if (!artifactType) return;
    openArtifact({
      id: `code-${code.length}-${code.slice(0, 32)}`,
      title: lang ? `${lang.charAt(0).toUpperCase() + lang.slice(1)} snippet` : "Code",
      type: artifactType,
      content: code,
      language: lang || undefined,
    });
  }, [artifactType, code, lang, openArtifact]);

  if (!match) {
    // Check if inline code looks like a file path
    const text = String(children).trim();
    const isFilePath = looksLikeFilePath(text);

    if (isFilePath) {
      const hasFullPath = /[/\\]/.test(text);
      const canPreview = isPreviewableFile(text);

      // Full path + previewable → clickable with artifact preview
      if (hasFullPath && canPreview) {
        const artifacts = useArtifactStore.getState().artifacts;
        const fileName = text.split(/[\\/]/).pop() || text;
        const existing = artifacts.find(
          (a) => a.filePath?.endsWith(fileName) || a.title === fileName,
        );

        const handleOpen = () => {
          if (existing) {
            openArtifact(existing);
          } else {
            const type = artifactTypeFromExtension(text) || "code";
            openArtifact({
              id: `file-preview-${text}`,
              title: fileName,
              type: type === "react" || type === "html" || type === "svg" || type === "mermaid" || type === "markdown" ? type : "file-preview",
              content: "",
              language: languageFromExtension(text),
              filePath: text,
            });
          }
        };

        return (
          <button
            type="button"
            onClick={handleOpen}
            className="inline-flex items-center gap-1 rounded-md bg-[var(--surface-tertiary)] px-1.5 py-0.5 text-[0.85em] font-mono border border-[var(--border-default)] hover:bg-[var(--surface-secondary)] hover:border-[var(--border-hover)] transition-colors cursor-pointer"
            title="Open file preview"
          >
            <FileText className="h-3 w-3 text-[var(--text-tertiary)] shrink-0" />
            <span>{children}</span>
          </button>
        );
      }

      // Full path + non-previewable → clickable with system open
      if (hasFullPath) {
        const handleSystemOpen = () => {
          api.post(API.FILES.OPEN_SYSTEM, { path: text }).catch(() => {});
        };

        return (
          <button
            type="button"
            onClick={handleSystemOpen}
            className="inline-flex items-center gap-1 rounded-md bg-[var(--surface-tertiary)] px-1.5 py-0.5 text-[0.85em] font-mono border border-[var(--border-default)] hover:bg-[var(--surface-secondary)] hover:border-[var(--border-hover)] transition-colors cursor-pointer"
            title="Open with system application"
          >
            <ExternalLink className="h-3 w-3 text-[var(--text-tertiary)] shrink-0" />
            <span>{children}</span>
          </button>
        );
      }

      // Bare filename (no path separator) → styled with file icon, not clickable
      return (
        <span className="inline-flex items-center gap-1 rounded-md bg-[var(--surface-tertiary)] px-1.5 py-0.5 text-[0.85em] font-mono border border-[var(--border-default)]">
          <FileText className="h-3 w-3 text-[var(--text-tertiary)] shrink-0" />
          <span>{children}</span>
        </span>
      );
    }

    // Regular inline code
    return (
      <code
        className="rounded-md bg-[var(--surface-tertiary)] px-1.5 py-0.5 text-[0.85em] font-mono border border-[var(--border-default)]"
        {...props}
      >
        {children}
      </code>
    );
  }

  // Detect mermaid code blocks
  if (lang === "mermaid") {
    return <MermaidBlock code={code} />;
  }

  // Code block
  const langDisplay = lang
    ? lang.charAt(0).toUpperCase() + lang.slice(1).toLowerCase()
    : "Code";

  return (
    <div className="group relative rounded-2xl overflow-hidden my-4 bg-[var(--code-block-bg)]">
      <div className="flex items-center justify-between px-5 py-1.5">
        <div className="flex items-center gap-2.5">
          <svg className="w-4 h-4 text-[var(--code-block-text)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-sm font-sans text-[var(--code-block-text)] select-none">{langDisplay}</span>
        </div>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          {artifactType && (
            <button
              onClick={handleOpenInPanel}
              className="p-2 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 text-[var(--code-block-text)] hover:text-[var(--code-block-text-hover)] transition-colors"
              title="Open in panel"
            >
              <PanelRight className="h-5 w-5" />
            </button>
          )}
          <button
            onClick={handleCopy}
            className="p-2 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 text-[var(--code-block-text)] hover:text-[var(--code-block-text-hover)] transition-colors"
            title={copied ? "Copied!" : "Copy code"}
          >
            {copied ? (
              <Check className="h-5 w-5 text-[var(--code-block-success)]" />
            ) : (
              <Copy className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>
      <div className="px-5 pb-4">
        <pre className="overflow-x-auto text-sm leading-relaxed">
          <code className={`font-mono ${className}`} {...props}>
            {children}
          </code>
        </pre>
      </div>
    </div>
  );
}

export const TextPart = memo(function TextPart({ data, isStreaming, sources = [] }: TextPartProps) {
  // Build a URL→Source lookup for inline citation matching
  const sourceMap = useMemo(() => {
    const map = new Map<string, Source>();
    for (const s of sources) {
      map.set(s.url, s);
    }
    return map;
  }, [sources]);

  const components = useMemo(
    () => ({
      code: CodeBlock,
      // Render matched links as citation badges, otherwise open in new tab
      a: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { children?: React.ReactNode }) => {
        const source = href ? sourceMap.get(href) : undefined;
        if (source) {
          return (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="no-underline"
              {...props}
            >
              <span className="inline-flex items-center gap-1 rounded-full bg-[var(--surface-tertiary)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer align-middle mx-0.5">
                {source.favicon && (
                  <img src={source.favicon} alt="" className="h-3.5 w-3.5 rounded-sm" loading="lazy" />
                )}
                <span className="truncate max-w-[150px]">{source.domain}</span>
              </span>
            </a>
          );
        }
        return (
          <a target="_blank" rel="noopener noreferrer" href={href} {...props}>
            {children}
          </a>
        );
      },
    }),
    [sourceMap],
  );

  // Skip expensive syntax highlighting during streaming — code blocks are
  // still growing so highlighting is wasted work. Full highlighting runs
  // once streaming finishes (isStreaming becomes false).
  const rehypePlugins = useMemo(
    () => (isStreaming ? [] : [rehypeHighlight]),
    [isStreaming],
  );

  if (!data.text) return null;

  return (
    <div className={cn(
      "prose max-w-none text-[var(--text-primary)] leading-relaxed",
      isStreaming && "streaming-cursor",
    )}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {data.text}
      </ReactMarkdown>
    </div>
  );
});

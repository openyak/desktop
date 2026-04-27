"use client";

import { useCallback, useState } from "react";
import {
  FileText,
  FileSpreadsheet,
  Code,
  Globe,
  Image,
  LayoutDashboard,
  GitBranch,
  Download,
  Loader2,
  Presentation,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useArtifactStore } from "@/stores/artifact-store";
import { apiFetch } from "@/lib/api";
import { API } from "@/lib/constants";
import type { ToolPart } from "@/types/message";
import type { ArtifactType } from "@/types/artifact";

const ARTIFACT_TYPE_CONFIG: Record<
  string,
  { icon: React.ComponentType<{ className?: string }>; label: string }
> = {
  react:    { icon: LayoutDashboard, label: "Component \u00b7 TSX" },
  html:     { icon: Globe,           label: "Page \u00b7 HTML" },
  svg:      { icon: Image,           label: "Image \u00b7 SVG" },
  code:     { icon: Code,            label: "Code" },
  markdown: { icon: FileText,        label: "Document \u00b7 MD" },
  mermaid:  { icon: GitBranch,       label: "Diagram \u00b7 Mermaid" },
  docx:     { icon: FileText,        label: "Document \u00b7 Word" },
  xlsx:     { icon: FileSpreadsheet, label: "Spreadsheet \u00b7 Excel" },
  pdf:      { icon: FileText,        label: "Document \u00b7 PDF" },
  pptx:     { icon: Presentation,    label: "Presentation \u00b7 PPTX" },
  csv:      { icon: FileSpreadsheet, label: "Spreadsheet \u00b7 CSV" },
};

interface ArtifactCardProps {
  data: ToolPart;
}

export function ArtifactCard({ data }: ArtifactCardProps) {
  const openArtifact = useArtifactStore((s) => s.openArtifact);
  const input = data.state.input as Record<string, string | undefined>;
  const metadata = (data.state.metadata ?? {}) as Record<string, string | undefined>;
  const command = input.command || metadata.command || "create";

  // For update/rewrite, content is in metadata (not in input args)
  const artifactType = (input.type ?? metadata.type ?? "code") as string;
  const title = input.title ?? metadata.title ?? data.state.title ?? "Untitled";
  const content = input.content ?? metadata.content ?? "";
  const language = input.language ?? metadata.language;
  const identifier = input.identifier ?? metadata.identifier;

  const isRunning = data.state.status === "running" || data.state.status === "pending";
  const isError = data.state.status === "error";
  const [downloading, setDownloading] = useState(false);

  const config = ARTIFACT_TYPE_CONFIG[artifactType] ?? ARTIFACT_TYPE_CONFIG.code;
  const TypeIcon = config.icon;
  const baseLabel =
    artifactType === "code" && language
      ? `Code \u00b7 ${language.charAt(0).toUpperCase() + language.slice(1)}`
      : config.label;
  const commandSuffix =
    command === "update" ? " (edited)" : command === "rewrite" ? " (rewritten)" : "";
  const typeLabel = baseLabel + commandSuffix;

  const handleClick = useCallback(() => {
    if (!content) return;
    openArtifact({
      id: data.call_id,
      type: artifactType as ArtifactType,
      title,
      content,
      language,
      identifier,
    });
  }, [openArtifact, data.call_id, artifactType, title, content, language, identifier]);

  const sanitizedTitle = title.replace(/[^a-zA-Z0-9_\u4e00-\u9fff-]/g, "_");

  const downloadBlob = useCallback((blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, []);

  const handleDownload = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();

      // Markdown → download as PDF via backend
      if (artifactType === "markdown") {
        setDownloading(true);
        try {
          const res = await apiFetch(API.ARTIFACTS.EXPORT_PDF, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content, title }),
            timeoutMs: 120_000,
          });
          if (!res.ok) throw new Error("PDF export failed");
          const blob = await res.blob();
          downloadBlob(blob, `${sanitizedTitle}.pdf`);
        } catch {
          // Fallback to .md download
          const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
          downloadBlob(blob, `${sanitizedTitle}.md`);
        } finally {
          setDownloading(false);
        }
        return;
      }

      // Other types → direct download
      const extMap: Record<string, string> = {
        react: "tsx",
        html: "html",
        svg: "svg",
        code: language ?? "txt",
        mermaid: "mmd",
        csv: "csv",
      };
      const ext = extMap[artifactType] ?? "txt";
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      downloadBlob(blob, `${sanitizedTitle}.${ext}`);
    },
    [content, title, sanitizedTitle, artifactType, language, downloadBlob],
  );

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "flex items-center gap-3 w-full rounded-xl border px-4 py-3",
        "bg-[var(--surface-secondary)] hover:bg-[var(--surface-tertiary)]",
        "hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5 transition-all duration-150",
        "text-left group",
        isError
          ? "border-[var(--color-destructive)]/30"
          : "border-[var(--border-default)]",
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "flex items-center justify-center h-9 w-9 rounded-lg shrink-0",
          "bg-[var(--surface-tertiary)]",
        )}
      >
        {isRunning ? (
          <Loader2 className="h-4 w-4 text-[var(--text-tertiary)] animate-spin" />
        ) : (
          <TypeIcon className="h-4 w-4 text-[var(--brand-primary)]" />
        )}
      </div>

      {/* Title + type */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm font-medium text-[var(--text-primary)] truncate",
            isRunning && "shimmer-text",
          )}
        >
          {title}
        </p>
        <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{typeLabel}</p>
      </div>

      {/* Download */}
      {!isRunning && !isError && content && (
        <span
          role="button"
          tabIndex={0}
          onClick={handleDownload}
          onKeyDown={(e) => e.key === "Enter" && handleDownload(e as unknown as React.MouseEvent)}
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium shrink-0",
            "text-[var(--text-secondary)] bg-[var(--surface-tertiary)]",
            "hover:bg-[var(--surface-primary)] hover:text-[var(--text-primary)]",
            "transition-colors cursor-pointer",
            downloading && "opacity-60 pointer-events-none",
          )}
        >
          {downloading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Download className="h-3.5 w-3.5" />
          )}
          <span>{downloading ? "Exporting…" : "Download"}</span>
        </span>
      )}
    </button>
  );
}

"use client";

import { useCallback, useMemo, useState } from "react";
import {
  Code,
  Download,
  FileArchive,
  FileSpreadsheet,
  FileText,
  Globe,
  Image,
  Loader2,
  Presentation,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { API } from "@/lib/constants";
import { artifactTypeFromExtension, languageFromExtension } from "@/lib/artifacts";
import { useArtifactStore } from "@/stores/artifact-store";
import { useWorkspaceStore } from "@/stores/workspace-store";
import type { ArtifactType } from "@/types/artifact";
import type { ToolPart } from "@/types/message";

interface FileArtifactCardProps {
  data?: ToolPart;
  filePath?: string;
  title?: string;
  cardId?: string;
  compact?: boolean;
}

interface BinaryContentResponse {
  content_base64: string;
  name: string;
  mime_type: string;
  size: number;
}

const TYPE_CONFIG: Record<
  string,
  { icon: React.ComponentType<{ className?: string }>; label: string }
> = {
  html: { icon: Globe, label: "Page · HTML" },
  svg: { icon: Image, label: "Image · SVG" },
  markdown: { icon: FileText, label: "Document · MD" },
  docx: { icon: FileText, label: "Document · Word" },
  pdf: { icon: FileText, label: "Document · PDF" },
  pptx: { icon: Presentation, label: "Presentation · PPTX" },
  xlsx: { icon: FileSpreadsheet, label: "Spreadsheet · Excel" },
  csv: { icon: FileSpreadsheet, label: "Spreadsheet · CSV" },
  mermaid: { icon: Code, label: "Diagram · Mermaid" },
  react: { icon: Code, label: "Component · TSX" },
  code: { icon: Code, label: "Code" },
  file: { icon: FileArchive, label: "File" },
};

function basename(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

function titleWithoutExtension(name: string): string {
  return name.replace(/\.[^.]+$/, "");
}

function labelForFile(filePath: string, artifactType: ArtifactType | null): string {
  if (artifactType === "code") {
    const language = languageFromExtension(filePath);
    return language ? `Code · ${language.charAt(0).toUpperCase() + language.slice(1)}` : "Code";
  }
  return TYPE_CONFIG[artifactType ?? "file"]?.label ?? TYPE_CONFIG.file.label;
}

function artifactPanelType(filePath: string): ArtifactType {
  return artifactTypeFromExtension(filePath) ?? "file-preview";
}

function base64ToBlob(base64: string, mimeType: string): Blob {
  const binary = window.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mimeType || "application/octet-stream" });
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function FileArtifactCard({
  data,
  filePath: directFilePath,
  title: directTitle,
  cardId,
  compact = false,
}: FileArtifactCardProps) {
  const openArtifact = useArtifactStore((s) => s.openArtifact);
  const workspace = useWorkspaceStore((s) => s.activeWorkspacePath);
  const [downloading, setDownloading] = useState(false);

  const input = (data?.state.input ?? {}) as Record<string, string | undefined>;
  const metadata = (data?.state.metadata ?? {}) as Record<string, string | undefined>;
  const filePath = directFilePath || metadata.file_path || input.file_path || "";
  const fileName = filePath ? basename(filePath) : "File";
  const title = directTitle || metadata.title || input.title || titleWithoutExtension(fileName);
  const isRunning = data?.state.status === "running" || data?.state.status === "pending";
  const isError = data?.state.status === "error";

  const artifactType = useMemo(() => (filePath ? artifactTypeFromExtension(filePath) : null), [filePath]);
  const typeLabel = filePath ? labelForFile(filePath, artifactType) : "File";
  const config = TYPE_CONFIG[artifactType ?? "file"] ?? TYPE_CONFIG.file;
  const TypeIcon = config.icon;

  const handleOpen = useCallback(() => {
    if (!filePath || isRunning || isError) return;
    openArtifact({
      id: cardId || `present-${data?.call_id ?? filePath}`,
      type: artifactPanelType(filePath),
      title: title || fileName,
      content: "",
      language: languageFromExtension(filePath),
      filePath,
    });
  }, [cardId, data?.call_id, fileName, filePath, isError, isRunning, openArtifact, title]);

  const handleDownload = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!filePath || downloading) return;

      setDownloading(true);
      try {
        const res = await api.post<BinaryContentResponse>(
          API.FILES.CONTENT_BINARY,
          { path: filePath, workspace },
          { timeoutMs: 120_000 },
        );
        downloadBlob(base64ToBlob(res.content_base64, res.mime_type), res.name || fileName);
      } finally {
        setDownloading(false);
      }
    },
    [downloading, fileName, filePath, workspace],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleOpen();
      }
    },
    [handleOpen],
  );

  return (
    <div
      role="button"
      tabIndex={isRunning || isError ? -1 : 0}
      onClick={handleOpen}
      onKeyDown={handleKeyDown}
      className={cn(
        "group flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left",
        "bg-[var(--surface-secondary)] transition-all duration-150",
        !isRunning && !isError && "cursor-pointer hover:-translate-y-0.5 hover:bg-[var(--surface-tertiary)] hover:shadow-[var(--shadow-md)]",
        isError ? "border-[var(--color-destructive)]/30" : "border-[var(--border-default)]",
        compact && "min-h-[5.25rem]",
      )}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--surface-tertiary)]">
        {isRunning ? (
          <Loader2 className="h-4 w-4 animate-spin text-[var(--text-tertiary)]" />
        ) : (
          <TypeIcon className="h-4 w-4 text-[var(--brand-primary)]" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "truncate text-sm font-medium text-[var(--text-primary)]",
            isRunning && "shimmer-text",
          )}
          title={title || fileName}
        >
          {title || fileName}
        </p>
        <p className="mt-0.5 truncate text-xs text-[var(--text-tertiary)]" title={fileName}>
          {typeLabel}
        </p>
      </div>

      {!isRunning && !isError && filePath && (
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading}
          aria-label={`${downloading ? "Exporting" : "Download"} ${title || fileName}`}
          className={cn(
            "flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium",
            "bg-[var(--surface-tertiary)] text-[var(--text-secondary)] transition-colors",
            "hover:bg-[var(--surface-primary)] hover:text-[var(--text-primary)]",
            compact && "px-2.5",
            downloading && "opacity-60",
          )}
        >
          {downloading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Download className="h-3.5 w-3.5" />
          )}
          {!compact && <span>{downloading ? "Exporting…" : "Download"}</span>}
        </button>
      )}
    </div>
  );
}

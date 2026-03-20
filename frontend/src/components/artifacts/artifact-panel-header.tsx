"use client";

import { X, ChevronLeft, ChevronRight, Code, FileText, FileSpreadsheet, Globe, Image, LayoutDashboard, GitBranch, Presentation } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useArtifactStore } from "@/stores/artifact-store";
import type { ArtifactType } from "@/types/artifact";

const TYPE_CONFIG: Record<ArtifactType, { icon: React.ComponentType<{ className?: string }>; label: string }> = {
  react: { icon: LayoutDashboard, label: "React" },
  html: { icon: Globe, label: "HTML" },
  svg: { icon: Image, label: "SVG" },
  code: { icon: Code, label: "Code" },
  markdown: { icon: FileText, label: "Markdown" },
  mermaid: { icon: GitBranch, label: "Diagram" },
  docx: { icon: FileText, label: "Document" },
  xlsx: { icon: FileSpreadsheet, label: "Spreadsheet" },
  pdf: { icon: FileText, label: "PDF" },
  pptx: { icon: Presentation, label: "Slides" },
  csv: { icon: FileSpreadsheet, label: "CSV" },
  "file-preview": { icon: FileText, label: "File" },
};

export function ArtifactPanelHeader() {
  const activeArtifact = useArtifactStore((s) => s.activeArtifact);
  const artifacts = useArtifactStore((s) => s.artifacts);
  const activeIndex = useArtifactStore((s) => s.activeIndex);
  const close = useArtifactStore((s) => s.close);
  const goNext = useArtifactStore((s) => s.goNext);
  const goPrev = useArtifactStore((s) => s.goPrev);
  const versionHistory = useArtifactStore((s) => s.versionHistory);
  const activeVersionIndex = useArtifactStore((s) => s.activeVersionIndex);
  const goToVersion = useArtifactStore((s) => s.goToVersion);

  if (!activeArtifact) return null;

  const config = TYPE_CONFIG[activeArtifact.type] || TYPE_CONFIG.code;
  const TypeIcon = config.icon;
  const hasPrev = activeIndex > 0;
  const hasNext = activeIndex < artifacts.length - 1;

  // Version navigation
  const versions = activeArtifact.identifier
    ? versionHistory.get(activeArtifact.identifier) ?? []
    : [];
  const hasVersions = versions.length > 1;

  return (
    <div className="flex items-center justify-between h-12 px-4 shrink-0 border-b border-[var(--border-default)]">
      <div className="flex items-center gap-2 min-w-0">
        {/* Type badge */}
        <span className="flex items-center gap-1 rounded-md bg-[var(--surface-tertiary)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wide shrink-0">
          <TypeIcon className="h-3 w-3" />
          {config.label}
        </span>
        {/* Title */}
        <span className="text-sm font-medium text-[var(--text-primary)] truncate">
          {activeArtifact.title}
        </span>
        {/* Version selector */}
        {hasVersions && (
          <div className="flex items-center gap-0.5 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => goToVersion(activeVersionIndex - 1)}
              disabled={activeVersionIndex <= 0}
            >
              <ChevronLeft className="h-3 w-3" />
            </Button>
            <span className="text-[10px] text-[var(--text-tertiary)] tabular-nums whitespace-nowrap">
              v{activeVersionIndex + 1} of {versions.length}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => goToVersion(activeVersionIndex + 1)}
              disabled={activeVersionIndex >= versions.length - 1}
            >
              <ChevronRight className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {/* Prev/Next navigation */}
        {artifacts.length > 1 && (
          <>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={goPrev}
              disabled={!hasPrev}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-[10px] text-[var(--text-tertiary)] tabular-nums">
              {activeIndex + 1}/{artifacts.length}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={goNext}
              disabled={!hasNext}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </>
        )}
        {/* Close */}
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={close}>
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

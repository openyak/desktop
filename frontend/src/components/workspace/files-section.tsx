"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronRight, FileText, FolderOpen } from "lucide-react";
import { useWorkspaceStore, type WorkspaceFile } from "@/stores/workspace-store";
import { useArtifactStore } from "@/stores/artifact-store";
import { cn } from "@/lib/utils";

function FileItem({ file }: { file: WorkspaceFile }) {
  const handleClick = () => {
    const store = useArtifactStore.getState();
    // Match by filePath first, then fall back to matching by title (for artifacts
    // created by the artifact tool which don't have filePath set yet)
    const baseName = file.name.replace(/\.[^.]+$/, "");
    const existing = store.artifacts.find(
      (a) => a.filePath === file.path || (!a.filePath && a.title === baseName),
    );
    if (existing) {
      // Re-open with filePath set so future lookups match directly
      store.openArtifact({ ...existing, filePath: file.path });
      return;
    }
    store.openArtifact({
      id: `workspace-${file.path}`,
      type: "file-preview",
      title: file.name,
      content: "",
      filePath: file.path,
    });
  };

  const displayName =
    file.type === "instructions" ? `Instructions \u00b7 ${file.name}` : file.name;

  return (
    <button
      className="w-full flex items-center gap-2.5 px-4 py-1.5 text-left transition-colors"
      onClick={handleClick}
    >
      <FileText className="h-4 w-4 shrink-0 text-[var(--text-tertiary)]" />
      <span className="text-[13px] text-[var(--text-secondary)] truncate">
        {displayName}
      </span>
    </button>
  );
}

function Scratchpad() {
  const content = useWorkspaceStore((s) => s.scratchpadContent);
  const setContent = useWorkspaceStore((s) => s.setScratchpadContent);
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mx-4 mb-3">
      <button
        className={cn(
          "flex items-center gap-1.5 w-full px-3 py-2 rounded-lg text-left transition-colors",
          "border",
          expanded
            ? "border-[var(--border-focus)] bg-[var(--surface-primary)]"
            : "border-[var(--border-default)] hover:border-[var(--text-tertiary)]",
        )}
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 text-[var(--text-tertiary)]" />
        ) : (
          <ChevronRight className="h-3 w-3 text-[var(--text-tertiary)]" />
        )}
        <span className="text-[13px] text-[var(--text-tertiary)]">
          Scratchpad
        </span>
      </button>
      {expanded && (
        <textarea
          className={cn(
            "w-full mt-1.5 px-3 py-2 text-[13px] leading-relaxed rounded-lg resize-none",
            "bg-[var(--surface-primary)] text-[var(--text-primary)]",
            "placeholder:text-[var(--text-quaternary)]",
            "border border-[var(--border-focus)] focus:outline-none",
            "min-h-[80px]",
          )}
          placeholder="Notes, ideas, reminders..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          autoFocus
        />
      )}
    </div>
  );
}

export function FilesCard() {
  const workspaceFiles = useWorkspaceStore((s) => s.workspaceFiles);
  const scratchpadContent = useWorkspaceStore((s) => s.scratchpadContent);
  const collapsed = useWorkspaceStore((s) => s.collapsedSections["files"]);
  const toggleSection = useWorkspaceStore((s) => s.toggleSection);
  const hasContent = workspaceFiles.length > 0 || scratchpadContent.trim().length > 0;
  const latestFile = workspaceFiles[workspaceFiles.length - 1];

  return (
    <div className="overflow-hidden rounded-3xl border border-white/8 bg-white/[0.03] shadow-[0_0_0_1px_rgba(255,255,255,0.02)_inset] backdrop-blur-sm">
      <button
        className="flex w-full items-start justify-between px-4 py-4 text-left transition-colors hover:bg-white/[0.02]"
        onClick={() => toggleSection("files")}
      >
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl border border-white/8 bg-white/[0.04]">
            <FolderOpen className="h-4 w-4 text-[var(--text-tertiary)]" />
          </div>
          <div className="min-w-0">
            <span className="block text-[13px] font-medium text-[var(--text-primary)]">
              Files
            </span>
            <span className="mt-1 block text-[12px] text-[var(--text-tertiary)]">
              {workspaceFiles.length > 0
                ? `${workspaceFiles.length} generated file${workspaceFiles.length === 1 ? "" : "s"}`
                : hasContent
                  ? "Notes available"
                  : "No files yet"}
            </span>
            {latestFile && (
              <span className="mt-2 block truncate text-[12px] text-[var(--text-secondary)]">
                Latest: {latestFile.name}
              </span>
            )}
          </div>
        </div>
        <div className="ml-3 flex items-center gap-2">
          {workspaceFiles.length > 0 && (
            <span className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] font-medium text-[var(--text-tertiary)]">
              {workspaceFiles.length}
            </span>
          )}
          <ChevronDown
            className={cn(
              "h-4 w-4 text-[var(--text-tertiary)] transition-transform duration-200",
              collapsed && "-rotate-90",
            )}
          />
        </div>
      </button>
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/6 pb-1 pt-2">
              {workspaceFiles.length > 0 ? (
                <div className="space-y-0.5">
                  {workspaceFiles.map((file) => (
                    <FileItem key={file.path} file={file} />
                  ))}
                </div>
              ) : (
                <p className="px-4 py-2 text-[12px] text-[var(--text-quaternary)]">
                  No files yet
                </p>
              )}
              <div className="mt-2">
                <Scratchpad />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

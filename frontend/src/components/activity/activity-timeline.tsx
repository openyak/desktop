"use client";

import { useState } from "react";
import {
  FileText,
  Play,
  Search,
  Pencil,
  FolderSearch,
  Globe,
  HelpCircle,
  ListTodo,
  Layers,
  CheckCircle2,
  XCircle,
  ChevronDown,
  Wrench,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { cn } from "@/lib/utils";
import type { ToolPart } from "@/types/message";

const TOOL_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  read: FileText,
  write: FileText,
  edit: Pencil,
  bash: Play,
  glob: FolderSearch,
  grep: Search,
  web_fetch: Globe,
  web_search: Globe,
  question: HelpCircle,
  todo: ListTodo,
  task: Layers,
};

function getToolTitle(data: ToolPart, t: TFunction): string {
  if (data.state.title) return data.state.title;
  const input = data.state.input as Record<string, string | undefined>;
  switch (data.tool) {
    case "read":
      return t("toolRead", { name: getFileName(input.file_path) ?? t("file") });
    case "write":
      return t("toolWrite", { name: getFileName(input.file_path) ?? t("file") });
    case "edit":
      return t("toolEdit", { name: getFileName(input.file_path) ?? t("file") });
    case "bash":
      return t("toolRunCommand");
    case "glob":
      return t("toolSearchFiles");
    case "grep":
      return t("toolSearch", { query: input.pattern ?? "" });
    case "web_search":
      return t("toolWebSearch", { query: truncate(String(input.query ?? ""), 40) });
    case "web_fetch":
      return t("toolFetch", { url: truncate(String(input.url ?? ""), 40) });
    case "task":
      return input.description ?? t("toolSubtask");
    default:
      return data.tool;
  }
}

function getFileName(filePath?: string): string | null {
  if (!filePath) return null;
  const parts = filePath.replace(/\\/g, "/").split("/");
  return parts[parts.length - 1];
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 3) + "..." : s;
}

function getElapsed(tool: ToolPart): string {
  if (!tool.state.time_start || !tool.state.time_end) return "";
  const ms =
    new Date(tool.state.time_end).getTime() -
    new Date(tool.state.time_start).getTime();
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

interface TimelineItemProps {
  tool: ToolPart;
}

function TimelineItem({ tool }: TimelineItemProps) {
  const { t } = useTranslation("chat");
  const [isOpen, setIsOpen] = useState(false);
  const ToolIcon = TOOL_ICONS[tool.tool] ?? Play;
  const isError = tool.state.status === "error";
  const elapsed = getElapsed(tool);
  const title = getToolTitle(tool, t);

  return (
    <div>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 py-1.5 px-2 rounded-lg text-xs hover:bg-[var(--surface-tertiary)] transition-colors"
      >
        {isError ? (
          <XCircle className="h-3.5 w-3.5 text-[var(--tool-error)] shrink-0" />
        ) : (
          <CheckCircle2 className="h-3.5 w-3.5 text-[var(--tool-completed)] shrink-0" />
        )}
        <ToolIcon className="h-3.5 w-3.5 text-[var(--text-tertiary)] shrink-0" />
        <span className="flex-1 text-left truncate text-[var(--text-secondary)]">
          {title}
        </span>
        {elapsed && (
          <span className="text-[10px] text-[var(--text-tertiary)] shrink-0">
            {elapsed}
          </span>
        )}
        <ChevronDown
          className={cn(
            "h-3 w-3 text-[var(--text-tertiary)] transition-transform duration-200 shrink-0",
            isOpen && "rotate-180",
          )}
        />
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="ml-5 mt-1 mb-2 rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] overflow-hidden">
              {Object.keys(tool.state.input).length > 0 && (
                <div className="border-b border-[var(--border-default)]">
                  <p className="px-3 py-1 text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider bg-[var(--surface-tertiary)]">
                    {t("input")}
                  </p>
                  <pre className="p-2 text-[11px] text-[var(--text-secondary)] overflow-x-auto font-mono leading-relaxed max-h-[150px] overflow-y-auto">
                    {JSON.stringify(tool.state.input, null, 2)}
                  </pre>
                </div>
              )}
              {tool.state.output && (
                <div>
                  <p className={cn(
                    "px-3 py-1 text-[10px] font-semibold uppercase tracking-wider bg-[var(--surface-tertiary)]",
                    isError ? "text-[var(--tool-error)]" : "text-[var(--tool-completed)]",
                  )}>
                    {t("output")}
                  </p>
                  <pre className="p-2 text-[11px] text-[var(--text-secondary)] overflow-x-auto font-mono leading-relaxed max-h-[200px] overflow-y-auto">
                    {tool.state.output.length > 3000
                      ? tool.state.output.slice(0, 3000) + "\n" + t("truncated")
                      : tool.state.output}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface ActivityTimelineProps {
  toolParts: ToolPart[];
}

export function ActivityTimeline({ toolParts }: ActivityTimelineProps) {
  const { t } = useTranslation("chat");

  if (toolParts.length === 0) return null;

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Wrench className="h-4 w-4 text-[var(--text-secondary)]" />
        <h3 className="text-sm font-medium text-[var(--text-primary)]">
          {t("tools")}
        </h3>
        <span className="text-[10px] text-[var(--text-tertiary)] bg-[var(--surface-tertiary)] rounded-full px-2 py-0.5">
          {toolParts.length}
        </span>
      </div>
      <div className="space-y-0.5">
        {toolParts.map((tool, i) => (
          <TimelineItem key={`${tool.call_id}-${i}`} tool={tool} />
        ))}
      </div>
    </div>
  );
}

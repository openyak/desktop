"use client";

import { useCallback, useMemo, useState } from "react";
import type { PartData, ToolPart, StepStartPart, StepFinishPart } from "@/types/message";
import { TextPart } from "@/components/parts/text-part";
import { ReasoningPart } from "@/components/parts/reasoning-part";
import { SubtaskPart } from "@/components/parts/subtask-part";
import { ArtifactCard } from "@/components/parts/artifact-card";
import { FileArtifactCard } from "@/components/parts/file-artifact-card";
import { PlanFileCard } from "@/components/parts/plan-file-card";
import { SourcesFooter } from "@/components/parts/sources-footer";
import { ActivitySummary } from "@/components/activity/activity-summary";
import { TodoProgress, type TodoItem } from "@/components/parts/todo-progress";
import { extractSources } from "@/lib/sources";
import { cn } from "@/lib/utils";
import type { ActivityData, ChainItem } from "@/stores/activity-store";

interface MessageContentProps {
  parts: PartData[];
  /** Whether this is the currently streaming message. */
  isStreaming?: boolean;
  /** Stable key identifying the message — used by ActivitySummary to toggle the activity panel. */
  activityKey?: string;
}

const VISIBLE_TOOL_PARTS = new Set(["artifact", "present_file", "submit_plan"]);
const FILE_CARD_TOOL_PARTS = new Set(["present_file", "write", "edit", "code_execute"]);
const GENERATED_FILE_TOOL_PARTS = new Set(["write", "edit", "code_execute"]);
const FILE_CARD_EXTENSIONS = new Set([
  ".csv",
  ".docx",
  ".html",
  ".htm",
  ".md",
  ".mdx",
  ".pdf",
  ".ppt",
  ".pptx",
  ".svg",
  ".tsv",
  ".txt",
  ".xls",
  ".xlsx",
]);
const NON_USER_FACING_FILE_HINTS = ["helper", "scratch", "temp", "tmp", "script"];

function isFileCardToolPart(part: PartData): boolean {
  return part.type === "tool" && FILE_CARD_TOOL_PARTS.has((part as ToolPart).tool);
}

function fileExtension(filePath: string): string {
  const lastSlash = Math.max(filePath.lastIndexOf("/"), filePath.lastIndexOf("\\"));
  const fileName = filePath.slice(lastSlash + 1);
  const dot = fileName.lastIndexOf(".");
  return dot >= 0 ? fileName.slice(dot).toLowerCase() : "";
}

function isUserFacingGeneratedFile(filePath: string): boolean {
  const lastSlash = Math.max(filePath.lastIndexOf("/"), filePath.lastIndexOf("\\"));
  const fileName = filePath.slice(lastSlash + 1).toLowerCase();
  if (!FILE_CARD_EXTENSIONS.has(fileExtension(filePath))) return false;
  return !NON_USER_FACING_FILE_HINTS.some((hint) => fileName.includes(hint));
}

function collectToolFilePaths(part: ToolPart): string[] {
  const input = part.state.input as Record<string, unknown>;
  const metadata = (part.state.metadata ?? {}) as Record<string, unknown>;

  if (part.tool === "present_file") {
    const filePath = metadata.file_path || input.file_path;
    return typeof filePath === "string" ? [filePath] : [];
  }

  if ((part.tool === "write" || part.tool === "edit") && typeof metadata.file_path === "string") {
    return [metadata.file_path];
  }

  if (part.tool === "code_execute" && Array.isArray(metadata.written_files)) {
    return metadata.written_files.filter((path): path is string => typeof path === "string");
  }

  return [];
}

function fileCardsForTool(part: ToolPart, presentedFilePaths: Set<string>) {
  const input = part.state.input as Record<string, unknown>;
  const metadata = (part.state.metadata ?? {}) as Record<string, unknown>;
  const title =
    typeof metadata.title === "string"
      ? metadata.title
      : typeof input.title === "string"
        ? input.title
        : undefined;

  return collectToolFilePaths(part)
    .filter((filePath) =>
      part.tool === "present_file"
        ? !!filePath
        : isUserFacingGeneratedFile(filePath) && !presentedFilePaths.has(filePath),
    )
    .map((filePath) => ({ filePath, title: part.tool === "present_file" ? title : undefined }));
}

/**
 * Content Parts Dispatcher — routes each part to the appropriate renderer.
 *
 * When streaming: reasoning + tools are folded into a single "Thinking" line.
 * When complete: reasoning + tools are folded into a single "Activity" summary.
 */
export function MessageContent({ parts, isStreaming, activityKey }: MessageContentProps) {
  // Thinking duration reported by ReasoningPart's live timer
  const [thinkingDuration, setThinkingDuration] = useState<number | undefined>();
  const handleDurationChange = useCallback((secs: number) => setThinkingDuration(secs), []);

  // Find the last text part index to pass isStreaming only to that one
  let lastTextIndex = -1;
  for (let i = parts.length - 1; i >= 0; i--) {
    if (parts[i].type === "text" && lastTextIndex === -1) {
      lastTextIndex = i;
      break;
    }
  }

  // Collect all reasoning texts into a single array
  const reasoningTexts = useMemo(
    () =>
      parts
        .filter((p): p is PartData & { type: "reasoning" } => p.type === "reasoning")
        .map((p) => p.text),
    [parts],
  );

  const toolParts = useMemo(
    () => parts.filter((p): p is ToolPart => p.type === "tool"),
    [parts],
  );

  const stepParts = useMemo(
    () =>
      parts.filter(
        (p): p is StepStartPart | StepFinishPart =>
          p.type === "step-start" || p.type === "step-finish",
      ),
    [parts],
  );

  const hasReasoning = reasoningTexts.length > 0;
  const hasTools = toolParts.length > 0;
  const hasActivity = hasReasoning || hasTools;

  const presentedFilePaths = useMemo(() => {
    const paths = new Set<string>();
    for (const part of toolParts) {
      if (part.tool !== "present_file") continue;
      for (const filePath of collectToolFilePaths(part)) {
        paths.add(filePath);
      }
    }
    return paths;
  }, [toolParts]);

  // Only show activity during streaming if there's meaningful content:
  // - At least one reasoning text with non-empty firstLine, OR
  // - At least one tool part (running or completed)
  const hasMeaningfulActivity = useMemo(() => {
    if (!hasActivity) return false;
    if (!isStreaming) return true; // Always show when message is complete

    // During streaming: check for meaningful content
    const hasReasoningContent = reasoningTexts.some(text => {
      // Mirror the firstLine extraction from reasoning-part.tsx:45
      const firstLine = text?.split(/[。.!\n]/)[0]?.trim() ?? "";
      return firstLine.length > 0;
    });

    return hasReasoningContent || toolParts.length > 0;
  }, [hasActivity, isStreaming, reasoningTexts, toolParts]);

  // Track whether the thinking section is still active (reasoning or tools running)
  // Build ordered chain from parts (preserves interleaving of reasoning + tools)
  const chain = useMemo<ChainItem[]>(() => {
    const items: ChainItem[] = [];
    for (const p of parts) {
      if (p.type === "reasoning") items.push({ type: "reasoning", text: (p as PartData & { type: "reasoning" }).text });
      else if (p.type === "tool") items.push({ type: "tool", data: p as ToolPart });
    }
    return items;
  }, [parts]);

  // Activity data for the summary/panel
  const activityData = useMemo<ActivityData | null>(
    () =>
      hasActivity
        ? {
            sourceKey: activityKey,
            reasoningTexts,
            toolParts,
            thinkingDuration,
            stepParts,
            hasVisibleOutput: parts.some((p) =>
              p.type === "text" ||
              p.type === "file" ||
              p.type === "compaction" ||
              p.type === "subtask" ||
              (p.type === "tool" && VISIBLE_TOOL_PARTS.has((p as ToolPart).tool)),
            ),
            chain,
          }
        : null,
    [hasActivity, reasoningTexts, toolParts, thinkingDuration, stepParts, chain, parts, activityKey],
  );

  // Content parts: text, subtask, and deliverable tool calls (shown as inline cards)
  // Exclude error-status artifact calls (e.g. failed update attempts) — they have no content to display
  const contentParts = useMemo(
    () =>
      parts.filter(
        (p) =>
          p.type !== "compaction" &&
          p.type !== "reasoning" &&
          p.type !== "step-start" &&
          p.type !== "step-finish" &&
          !(
            p.type === "tool" &&
            !VISIBLE_TOOL_PARTS.has((p as ToolPart).tool) &&
            !(
              GENERATED_FILE_TOOL_PARTS.has((p as ToolPart).tool) &&
              fileCardsForTool(p as ToolPart, presentedFilePaths).length > 0
            )
          ) &&
          !(p.type === "tool" && (p as ToolPart).tool === "artifact" && (p as ToolPart).state.status === "error"),
      ),
    [parts, presentedFilePaths],
  );

  // Extract sources from web_search / web_fetch tool parts for citation rendering
  const sources = useMemo(() => extractSources(parts), [parts]);

  // Extract latest todo list from the most recent todo tool call
  const latestTodos = useMemo<TodoItem[]>(() => {
    for (let i = toolParts.length - 1; i >= 0; i--) {
      const tp = toolParts[i];
      if (tp.tool === "todo" && tp.state.metadata?.todos) {
        return tp.state.metadata.todos as TodoItem[];
      }
    }
    return [];
  }, [toolParts]);

  return (
    <div className="space-y-3">
      {/* Reasoning + tools: only show inline while streaming */}
      {isStreaming && hasActivity && hasMeaningfulActivity && (
        <ReasoningPart
          texts={reasoningTexts}
          toolParts={toolParts}
          isStreaming={isStreaming}
          onDurationChange={handleDurationChange}
        />
      )}

      {/* Activity summary — replaces ReasoningPart once streaming is done */}
      {!isStreaming && activityData && <ActivitySummary data={activityData} />}

      {/* Todo progress — visible only while streaming, folds into activity summary when done */}
      {isStreaming && latestTodos.length > 0 && <TodoProgress todos={latestTodos} />}

      {/* Content parts (text, subtask, artifacts, presented files) */}
      {contentParts.map((part, contentIndex) => {
        if (isFileCardToolPart(part)) {
          if (contentIndex > 0 && isFileCardToolPart(contentParts[contentIndex - 1])) {
            return null;
          }

          const group: Array<{ filePath: string; title?: string; source: ToolPart }> = [];
          const seen = new Set<string>();
          for (let i = contentIndex; i < contentParts.length; i += 1) {
            const candidate = contentParts[i];
            if (!isFileCardToolPart(candidate)) break;
            for (const item of fileCardsForTool(candidate as ToolPart, presentedFilePaths)) {
              if (seen.has(item.filePath)) continue;
              seen.add(item.filePath);
              group.push({ ...item, source: candidate as ToolPart });
            }
          }

          if (group.length === 0) return null;

          const originalIndex = parts.indexOf(part);
          return (
            <div
              key={`present-file-group-${originalIndex}`}
              className={cn(
                "grid gap-2",
                group.length > 1 && "sm:grid-cols-2",
              )}
            >
              {group.map((item) => (
                <FileArtifactCard
                  key={`${item.source.call_id}-${item.filePath}`}
                  data={item.source}
                  filePath={item.filePath}
                  title={item.title}
                  cardId={`file-card-${item.source.call_id}-${item.filePath}`}
                  compact={group.length > 1}
                />
              ))}
            </div>
          );
        }

        const originalIndex = parts.indexOf(part);
        switch (part.type) {
          case "text":
            return (
              <TextPart
                key={originalIndex}
                data={part}
                isStreaming={isStreaming && originalIndex === lastTextIndex}
                sources={sources}
              />
            );
          case "subtask":
            return <SubtaskPart key={originalIndex} data={part} />;
          case "tool": {
            const tp = part as ToolPart;
            if (tp.tool === "submit_plan") return <PlanFileCard key={originalIndex} data={tp} />;
            return <ArtifactCard key={originalIndex} data={tp} />;
          }
          default:
            return null;
        }
      })}

      {/* Sources footer — shown progressively as tool results arrive */}
      {sources.length > 0 && (
        <SourcesFooter sources={sources} />
      )}
    </div>
  );
}

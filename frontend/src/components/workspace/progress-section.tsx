"use client";

import { CheckCircle2, Circle, Loader2, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import { useWorkspaceStore, type WorkspaceTodo } from "@/stores/workspace-store";
import { cn } from "@/lib/utils";

function TodoItem({ todo }: { todo: WorkspaceTodo }) {
  return (
    <div className="flex items-start gap-2.5 py-1">
      <div className="mt-0.5 shrink-0">
        {todo.status === "completed" ? (
          <CheckCircle2 className="h-4 w-4 text-[var(--tool-completed)]" />
        ) : todo.status === "in_progress" ? (
          <Loader2 className="h-4 w-4 text-[var(--text-accent)] animate-spin" />
        ) : (
          <Circle className="h-4 w-4 text-[var(--text-quaternary)]" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-[13px] leading-snug",
            todo.status === "completed"
              ? "text-[var(--text-tertiary)] line-through"
              : todo.status === "in_progress"
                ? "text-[var(--text-primary)]"
                : "text-[var(--text-secondary)]",
          )}
        >
          {todo.content}
        </p>
        {todo.status === "in_progress" && todo.activeForm && (
          <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5 animate-pulse">
            {todo.activeForm}
          </p>
        )}
      </div>
    </div>
  );
}

export function ProgressCard() {
  const { t } = useTranslation("chat");
  const todos = useWorkspaceStore((s) => s.todos);
  const collapsed = useWorkspaceStore((s) => s.collapsedSections["progress"]);
  const toggleSection = useWorkspaceStore((s) => s.toggleSection);
  const activeCount = todos.filter((todo) => todo.status !== "completed").length;
  const previewTodos = todos.slice(0, 3);

  if (todos.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-3xl border border-white/8 bg-white/[0.03] shadow-[0_0_0_1px_rgba(255,255,255,0.02)_inset] backdrop-blur-sm">
      <button
        className="flex w-full items-start justify-between px-4 py-4 text-left transition-colors hover:bg-white/[0.02]"
        onClick={() => toggleSection("progress")}
      >
        <div className="min-w-0 flex-1">
          <span className="block text-[13px] font-medium text-[var(--text-primary)]">
            Progress
          </span>
          <span className="mt-1 block text-[12px] text-[var(--text-tertiary)]">
            {activeCount === 0
              ? t("tasksCompleted", { count: todos.length })
              : t("activeTaskCount", { count: activeCount })}
          </span>
          <div className="mt-3 flex items-center gap-1.5">
            {previewTodos.map((todo, i) => (
              <div key={`${todo.content}-${i}`} className="flex items-center gap-1.5">
                <span
                  className={cn(
                    "h-6 w-6 rounded-full border flex items-center justify-center",
                    todo.status === "completed"
                      ? "border-white/20 bg-white/[0.06] text-[var(--tool-completed)]"
                      : todo.status === "in_progress"
                        ? "border-[var(--text-accent)]/50 bg-[var(--text-accent)]/10 text-[var(--text-accent)]"
                        : "border-white/15 text-[var(--text-quaternary)]",
                  )}
                >
                  {todo.status === "completed" ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : todo.status === "in_progress" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Circle className="h-3.5 w-3.5" />
                  )}
                </span>
                {i < previewTodos.length - 1 && (
                  <span className="h-px w-3 bg-white/10" />
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="ml-3 flex items-center gap-2">
          <span className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] font-medium text-[var(--text-tertiary)]">
            {todos.length}
          </span>
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
            <div className="border-t border-white/6 px-4 pb-4 pt-2 space-y-0.5">
              {todos.map((todo, i) => (
                <TodoItem key={`${todo.content}-${i}`} todo={todo} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

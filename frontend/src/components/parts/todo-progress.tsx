"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Circle, Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TodoItem {
  content: string;
  status: "pending" | "in_progress" | "completed";
  activeForm?: string;
}

interface TodoProgressProps {
  todos: TodoItem[];
}

const listVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.05, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 6 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  },
  exit: { opacity: 0, transition: { duration: 0.15 } },
};

export function TodoProgress({ todos }: TodoProgressProps) {
  const { completed, total } = useMemo(() => {
    const total = todos.length;
    const completed = todos.filter((t) => t.status === "completed").length;
    return { completed, total };
  }, [todos]);

  if (todos.length === 0) return null;

  return (
    <div className="space-y-2.5 py-1">
      {/* Segmented progress track + counter */}
      <div className="flex items-center gap-2.5">
        <div className="flex flex-1 gap-1">
          {todos.map((todo, i) => (
            <motion.div
              key={i}
              className="h-1 flex-1 rounded-full"
              animate={{
                backgroundColor:
                  todo.status === "completed"
                    ? "var(--text-primary)"
                    : todo.status === "in_progress"
                      ? "var(--text-tertiary)"
                      : "var(--surface-tertiary)",
                opacity:
                  todo.status === "in_progress" ? [0.4, 1, 0.4] : 1,
              }}
              transition={
                todo.status === "completed"
                  ? { type: "spring", stiffness: 300, damping: 30 }
                  : todo.status === "in_progress"
                    ? {
                        backgroundColor: { duration: 0.4 },
                        opacity: { duration: 2, ease: "easeInOut", repeat: Infinity },
                      }
                    : { duration: 0.4 }
              }
              title={todo.content}
            />
          ))}
        </div>
        <span className="text-[11px] font-medium text-[var(--text-tertiary)] tabular-nums shrink-0">
          {completed} of {total}
        </span>
      </div>

      {/* Todo items */}
      <motion.ul
        className="space-y-0.5"
        variants={listVariants}
        initial="hidden"
        animate="visible"
      >
        <AnimatePresence>
          {todos.map((todo, i) => {
            const isCompleted = todo.status === "completed";
            const isActive = todo.status === "in_progress";
            const displayText =
              isActive && todo.activeForm ? todo.activeForm : todo.content;

            return (
              <motion.li
                key={`${todo.content}-${i}`}
                layout
                variants={itemVariants}
                exit="exit"
                className={cn(
                  "flex items-center gap-2 py-0.5 text-[13px]",
                  isCompleted && "opacity-50",
                )}
              >
                {/* Icon */}
                {isCompleted ? (
                  <Check className="h-3.5 w-3.5 shrink-0 text-[var(--text-tertiary)]" />
                ) : isActive ? (
                  <span className="flex h-3.5 w-3.5 items-center justify-center shrink-0">
                    <span className="h-1.5 w-1.5 rounded-full bg-[var(--text-primary)]" />
                  </span>
                ) : (
                  <Circle className="h-3 w-3 shrink-0 text-[var(--text-tertiary)] opacity-60 ml-px" />
                )}

                {/* Text */}
                <span
                  className={cn(
                    "truncate",
                    isCompleted
                      ? "text-[var(--text-tertiary)]"
                      : isActive
                        ? "shimmer-text"
                        : "text-[var(--text-secondary)]",
                  )}
                  title={todo.content}
                >
                  {displayText}
                </span>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </motion.ul>
    </div>
  );
}

"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Minimize2, Check, Scissors, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CompactionPart as CompactionPartType, CompactionPhaseState } from "@/types/message";

interface CompactionPartProps {
  data?: CompactionPartType;
}

/* ── Animation variants (mirrored from todo-progress.tsx) ── */

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
    transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as const },
  },
  exit: { opacity: 0, transition: { duration: 0.15 } },
};

/* ── Phase display config ── */

const PHASE_CONFIG: Record<string, { label: string; activeLabel: string; icon: typeof Scissors }> = {
  prune: {
    label: "Prune old context",
    activeLabel: "Pruning old context…",
    icon: Scissors,
  },
  summarize: {
    label: "Summarize conversation",
    activeLabel: "Summarizing conversation…",
    icon: BookOpen,
  },
};

export function CompactionPart({ data }: CompactionPartProps) {
  const isRich = data?.phases && data.phases.length > 0;
  const isCompleted = !isRich || data?.compactionStatus === "completed";

  const { completed, total } = useMemo(() => {
    if (!data?.phases) return { completed: 0, total: 2 };
    const t = data.phases.length;
    const c = data.phases.filter((p) => p.status === "completed").length;
    return { completed: c, total: t };
  }, [data?.phases]);

  /* ── Completed state: compact single line with entry animation ── */
  if (isCompleted) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className="flex items-center gap-2 py-2 px-3 rounded-lg bg-[var(--surface-secondary)] text-[var(--text-tertiary)]"
      >
        <Check className="h-3.5 w-3.5 shrink-0" />
        <span className="text-[11px]">Context compressed to save tokens</span>
      </motion.div>
    );
  }

  /* ── In-progress state: phased progress display ── */
  const phases = data?.phases ?? [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-2.5 py-1.5 px-3 rounded-lg bg-[var(--surface-secondary)]"
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <Minimize2 className="h-3.5 w-3.5 shrink-0 text-[var(--text-tertiary)] shimmer-icon" />
        <span className="text-[11px] font-medium shimmer-text">Compressing context</span>
      </div>

      {/* Segmented progress bar (same pattern as todo-progress.tsx) */}
      <div className="flex items-center gap-2.5">
        <div className="flex flex-1 gap-1">
          {phases.map((phase, i) => (
            <motion.div
              key={i}
              className="h-1 flex-1 rounded-full"
              animate={{
                backgroundColor:
                  phase.status === "completed"
                    ? "var(--text-primary)"
                    : phase.status === "started"
                      ? "var(--text-tertiary)"
                      : "var(--surface-tertiary)",
                opacity: phase.status === "started" ? [0.4, 1, 0.4] : 1,
              }}
              transition={
                phase.status === "completed"
                  ? { type: "spring", stiffness: 300, damping: 30 }
                  : phase.status === "started"
                    ? {
                        backgroundColor: { duration: 0.4 },
                        opacity: { duration: 2, ease: "easeInOut", repeat: Infinity },
                      }
                    : { duration: 0.4 }
              }
            />
          ))}
        </div>
        <span className="text-[11px] font-medium text-[var(--text-tertiary)] tabular-nums shrink-0">
          {completed} of {total}
        </span>
      </div>

      {/* Phase items */}
      <motion.ul
        className="space-y-0.5"
        variants={listVariants}
        initial="hidden"
        animate="visible"
      >
        <AnimatePresence>
          {phases.map((phase) => {
            const config = PHASE_CONFIG[phase.phase];
            if (!config) return null;
            const PhaseIcon = config.icon;

            const isActive = phase.status === "started";
            const isDone = phase.status === "completed";
            const displayText = isActive ? config.activeLabel : config.label;

            return (
              <motion.li
                key={phase.phase}
                layout
                variants={itemVariants}
                exit="exit"
                className={cn(
                  "flex items-center gap-2 py-0.5 text-[13px]",
                  isDone && "opacity-50",
                )}
              >
                {/* Icon — three-state (mirrors todo-progress.tsx) */}
                {isDone ? (
                  <Check className="h-3.5 w-3.5 shrink-0 text-[var(--text-tertiary)]" />
                ) : isActive ? (
                  <span className="flex h-3.5 w-3.5 items-center justify-center shrink-0">
                    <span className="h-1.5 w-1.5 rounded-full bg-[var(--text-primary)]" />
                  </span>
                ) : (
                  <PhaseIcon className="h-3 w-3 shrink-0 text-[var(--text-tertiary)] opacity-60 ml-px" />
                )}

                {/* Text — shimmer for active, muted for done */}
                <span
                  className={cn(
                    "truncate",
                    isDone
                      ? "text-[var(--text-tertiary)]"
                      : isActive
                        ? "shimmer-text"
                        : "text-[var(--text-secondary)]",
                  )}
                >
                  {displayText}
                </span>

                {/* Progress for summarize phase */}
                {isActive && phase.phase === "summarize" && phase.chars != null && phase.chars > 0 && (
                  <span className="text-[10px] text-[var(--text-tertiary)] tabular-nums ml-auto">
                    {phase.chars}+ chars
                  </span>
                )}
              </motion.li>
            );
          })}
        </AnimatePresence>
      </motion.ul>
    </motion.div>
  );
}

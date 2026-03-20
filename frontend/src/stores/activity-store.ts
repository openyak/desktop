"use client";

import { create } from "zustand";
import type { ToolPart, StepStartPart, StepFinishPart } from "@/types/message";

/** A single item in the execution chain (preserves interleaving order). */
export type ChainItem =
  | { type: "reasoning"; text: string }
  | { type: "tool"; data: ToolPart };

export interface ActivityData {
  reasoningTexts: string[];
  toolParts: ToolPart[];
  thinkingDuration?: number;
  stepParts: (StepStartPart | StepFinishPart)[];
  /** Ordered chain of reasoning + tool items (preserves execution order). */
  chain: ChainItem[];
}

/** Derive wall-clock duration from tool timing (for history-loaded messages). */
export function computeDuration(data: ActivityData): number | undefined {
  if (data.thinkingDuration != null && data.thinkingDuration > 0) {
    return data.thinkingDuration;
  }
  const times: number[] = [];
  for (const tool of data.toolParts) {
    if (tool.state.time_start) times.push(new Date(tool.state.time_start).getTime());
    if (tool.state.time_end) times.push(new Date(tool.state.time_end).getTime());
  }
  if (times.length >= 2) {
    const ms = Math.max(...times) - Math.min(...times);
    return Math.round(ms / 1000);
  }
  return undefined;
}

interface ActivityStore {
  isOpen: boolean;
  activeData: ActivityData | null;
  openForMessage: (data: ActivityData) => void;
  toggleForMessage: (data: ActivityData) => void;
  close: () => void;
}

export const useActivityStore = create<ActivityStore>((set, get) => ({
  isOpen: false,
  activeData: null,
  openForMessage: (data) => {
    // Mutual exclusion: close artifact panel when activity opens
    try {
      const { useArtifactStore } = require("@/stores/artifact-store");
      useArtifactStore.getState().close();
    } catch {
      // Artifact store may not be available during SSR
    }
    // Mutual exclusion: close plan review panel
    try {
      const { usePlanReviewStore } = require("@/stores/plan-review-store");
      usePlanReviewStore.getState().close();
    } catch {
      // Plan review store may not be available during SSR
    }
    set({ isOpen: true, activeData: data });
  },
  toggleForMessage: (data) => {
    const { isOpen } = get();
    if (isOpen) {
      set({ isOpen: false });
    } else {
      // Mutual exclusion: close artifact panel
      try {
        const { useArtifactStore } = require("@/stores/artifact-store");
        useArtifactStore.getState().close();
      } catch {
        // Artifact store may not be available during SSR
      }
      // Mutual exclusion: close plan review panel
      try {
        const { usePlanReviewStore } = require("@/stores/plan-review-store");
        usePlanReviewStore.getState().close();
      } catch {
        // Plan review store may not be available during SSR
      }
      set({ isOpen: true, activeData: data });
    }
  },
  close: () => set({ isOpen: false }),
}));

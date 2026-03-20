"use client";

import { create } from "zustand";
import type { PlanReviewRequest } from "@/types/streaming";

interface PlanReviewStore {
  isOpen: boolean;
  /** Plan data stored here so it survives finishGeneration clearing chat store */
  planData: PlanReviewRequest | null;
  /** Panel width in pixels — defaults to half the viewport */
  panelWidth: number;

  openReview: (data: PlanReviewRequest) => void;
  close: () => void;
  updateWidth: () => void;
}

function getHalfViewport(): number {
  if (typeof window === "undefined") return 520;
  return Math.max(Math.floor(window.innerWidth / 2), 480);
}

export const usePlanReviewStore = create<PlanReviewStore>((set) => ({
  isOpen: false,
  planData: null,
  panelWidth: getHalfViewport(),

  openReview: (data) => {
    // Mutual exclusion: close artifact and activity panels
    try {
      const { useArtifactStore } = require("@/stores/artifact-store");
      useArtifactStore.getState().close();
    } catch {
      // May not be available during SSR
    }
    try {
      const { useActivityStore } = require("@/stores/activity-store");
      useActivityStore.getState().close();
    } catch {
      // May not be available during SSR
    }
    set({ isOpen: true, planData: data, panelWidth: getHalfViewport() });
  },

  close: () => set({ isOpen: false, planData: null }),

  updateWidth: () => set({ panelWidth: getHalfViewport() }),
}));

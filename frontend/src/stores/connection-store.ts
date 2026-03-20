"use client";

import { create } from "zustand";
import type { SSEConnectionStatus } from "@/lib/sse";

interface ConnectionStore {
  /** Current SSE connection status */
  status: SSEConnectionStatus | "idle";
  /** Whether the backend health check passed */
  backendReachable: boolean;
  setStatus: (status: SSEConnectionStatus | "idle") => void;
  setBackendReachable: (reachable: boolean) => void;
}

export const useConnectionStore = create<ConnectionStore>((set) => ({
  status: "idle",
  backendReachable: true,
  setStatus: (status) => set({ status }),
  setBackendReachable: (reachable) => set({ backendReachable: reachable }),
}));

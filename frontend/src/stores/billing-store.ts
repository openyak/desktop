"use client";

import { create } from "zustand";

type UpgradeReason = "quota_exceeded" | "credits_required" | null;

interface BillingStore {
  /** When non-null, the upgrade dialog is shown */
  upgradeReason: UpgradeReason;
  showUpgrade: (reason: "quota_exceeded" | "credits_required") => void;
  dismissUpgrade: () => void;
}

export const useBillingStore = create<BillingStore>()((set) => ({
  upgradeReason: null,
  showUpgrade: (reason) => set({ upgradeReason: reason }),
  dismissUpgrade: () => set({ upgradeReason: null }),
}));

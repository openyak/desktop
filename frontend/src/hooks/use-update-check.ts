"use client";

import { useCallback, useSyncExternalStore } from "react";
import { IS_DESKTOP } from "@/lib/constants";
import { desktopAPI } from "@/lib/tauri-api";

const CHECK_INTERVAL = 4 * 60 * 60 * 1000; // 4 hours
const STARTUP_DELAY = 5000; // 5 seconds
const DISMISSED_KEY = "openyak-dismissed-update";

interface UpdateState {
  available: boolean;
  version: string | null;
  notes: string | null;
  downloading: boolean;
  progress: number;
  dismissed: boolean;
  error: string | null;
}

interface UpdateInfo extends Omit<UpdateState, "dismissed"> {
  downloadAndInstall: () => Promise<void>;
  dismiss: () => void;
  checkNow: () => Promise<void>;
}

let state: UpdateState = {
  available: false,
  version: null,
  notes: null,
  downloading: false,
  progress: 0,
  dismissed: false,
  error: null,
};

const listeners = new Set<() => void>();
let pendingUpdate: unknown = null;
let initialized = false;

function setState(patch: Partial<UpdateState>) {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

export async function checkForUpdates() {
  if (!IS_DESKTOP) return;
  try {
    const { check } = await import("@tauri-apps/plugin-updater");
    const update = await check();
    if (!update) return;
    const dismissedVersion = localStorage.getItem(DISMISSED_KEY);
    if (dismissedVersion === update.version) return;
    pendingUpdate = update;
    setState({
      version: update.version,
      notes: update.body ?? null,
      available: true,
      dismissed: false,
    });
  } catch (e) {
    console.warn("Update check failed:", e);
  }
}

async function downloadAndInstall() {
  const update = pendingUpdate as {
    downloadAndInstall: (cb: (ev: {
      event: "Started" | "Progress" | "Finished";
      data: { contentLength?: number; chunkLength?: number };
    }) => void) => Promise<void>;
  } | null;
  if (!update) return;
  setState({ downloading: true, error: null });
  let totalLength = 0;
  let downloaded = 0;
  try {
    await update.downloadAndInstall((event) => {
      if (event.event === "Started" && event.data.contentLength) {
        totalLength = event.data.contentLength;
      } else if (event.event === "Progress") {
        downloaded += event.data.chunkLength ?? 0;
        if (totalLength > 0) {
          setState({ progress: Math.round((downloaded / totalLength) * 100) });
        }
      } else if (event.event === "Finished") {
        setState({ progress: 100 });
      }
    });
    const { relaunch } = await import("@tauri-apps/plugin-process");
    await relaunch();
  } catch (e) {
    console.error("Update install failed:", e);
    const message = e instanceof Error ? e.message : String(e);
    setState({ error: message, downloading: false });
  }
}

function dismiss() {
  if (state.version) localStorage.setItem(DISMISSED_KEY, state.version);
  setState({ dismissed: true, available: false });
}

function initOnce() {
  if (initialized || !IS_DESKTOP) return;
  initialized = true;
  setTimeout(checkForUpdates, STARTUP_DELAY);
  setInterval(checkForUpdates, CHECK_INTERVAL);
  desktopAPI.onCheckForUpdates(() => {
    void checkForUpdates();
  });
}

if (typeof window !== "undefined") {
  initOnce();
}

const serverSnapshot: UpdateState = {
  available: false,
  version: null,
  notes: null,
  downloading: false,
  progress: 0,
  dismissed: false,
  error: null,
};

export function useUpdateCheck(): UpdateInfo {
  const s = useSyncExternalStore(
    subscribe,
    () => state,
    () => serverSnapshot,
  );
  const boundDownload = useCallback(() => downloadAndInstall(), []);
  const boundDismiss = useCallback(() => dismiss(), []);
  const boundCheck = useCallback(() => checkForUpdates(), []);

  return {
    available: s.available && !s.dismissed,
    version: s.version,
    notes: s.notes,
    downloading: s.downloading,
    progress: s.progress,
    error: s.error,
    downloadAndInstall: boundDownload,
    dismiss: boundDismiss,
    checkNow: boundCheck,
  };
}

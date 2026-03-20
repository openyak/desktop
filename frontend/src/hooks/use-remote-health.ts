"use client";

/**
 * Remote connection health monitor.
 *
 * Polls an authenticated backend endpoint when in remote mode to detect:
 * - Network disconnects (tunnel died, phone lost signal)
 * - Auth failures (token rotated on desktop)
 *
 * Exposes a three-state model: "connected" | "limited" | "disconnected"
 * - connected: health check passed with valid auth
 * - limited: server reachable but auth failed (401/403)
 * - disconnected: server unreachable
 *
 * Visibility-aware: pauses polling when the tab/app is hidden.
 * Uses exponential backoff when disconnected (15s → 60s max).
 */

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { getRemoteConfig, isRemoteMode } from "@/lib/remote-connection";

export type RemoteHealthStatus = "connected" | "limited" | "disconnected" | "unknown";

const POLL_INTERVAL_CONNECTED = 15_000; // 15s when healthy
const POLL_INTERVAL_MAX = 60_000; // 60s max backoff
const POLL_BACKOFF_FACTOR = 2;

export function useRemoteHealth() {
  const [status, setStatus] = useState<RemoteHealthStatus>("unknown");
  const prevStatusRef = useRef<RemoteHealthStatus>("unknown");
  const intervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const delayRef = useRef(POLL_INTERVAL_CONNECTED);
  const activeRef = useRef(true);

  // Notify on status transitions
  const updateStatus = (next: RemoteHealthStatus) => {
    const prev = prevStatusRef.current;
    prevStatusRef.current = next;
    setStatus(next);

    // Only toast on bad transitions (skip initial "unknown" → anything)
    if (prev === "unknown") return;
    if (prev === "connected" && next === "disconnected") {
      toast.error("Connection lost to desktop");
    } else if (prev === "connected" && next === "limited") {
      toast.warning("Authentication failed — token may have been rotated");
    } else if (prev !== "connected" && next === "connected") {
      toast.success("Reconnected to desktop");
    }
  };

  useEffect(() => {
    if (!isRemoteMode()) {
      updateStatus("unknown");
      return;
    }

    activeRef.current = true;

    const check = async () => {
      if (!activeRef.current) return;
      const config = getRemoteConfig();
      if (!config) {
        updateStatus("disconnected");
        return;
      }

      try {
        // Use an /api/ endpoint so the auth middleware validates the token.
        // /health bypasses auth and would always return 200 even with an invalid token.
        const res = await fetch(`${config.url}/api/remote/provider-info`, {
          method: "GET",
          headers: { Authorization: `Bearer ${config.token}` },
          signal: AbortSignal.timeout(8000),
        });

        if (!activeRef.current) return;

        if (res.ok) {
          updateStatus("connected");
          delayRef.current = POLL_INTERVAL_CONNECTED;
        } else if (res.status === 401 || res.status === 403) {
          updateStatus("limited");
          delayRef.current = POLL_INTERVAL_CONNECTED;
        } else {
          updateStatus("disconnected");
          delayRef.current = Math.min(delayRef.current * POLL_BACKOFF_FACTOR, POLL_INTERVAL_MAX);
        }
      } catch {
        if (!activeRef.current) return;
        updateStatus("disconnected");
        delayRef.current = Math.min(delayRef.current * POLL_BACKOFF_FACTOR, POLL_INTERVAL_MAX);
      }

      scheduleNext();
    };

    const scheduleNext = () => {
      if (!activeRef.current) return;
      if (intervalRef.current) clearTimeout(intervalRef.current);
      intervalRef.current = setTimeout(check, delayRef.current);
    };

    // Visibility-aware: pause when hidden, resume immediately when visible
    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        // Came back — check immediately
        delayRef.current = POLL_INTERVAL_CONNECTED;
        check();
      } else {
        // Hidden — stop polling
        if (intervalRef.current) {
          clearTimeout(intervalRef.current);
          intervalRef.current = null;
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);

    // Initial check
    check();

    return () => {
      activeRef.current = false;
      document.removeEventListener("visibilitychange", handleVisibility);
      if (intervalRef.current) {
        clearTimeout(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  return status;
}

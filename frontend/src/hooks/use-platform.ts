"use client";

import { useEffect, useState } from "react";
import { IS_DESKTOP } from "@/lib/constants";
import { desktopAPI } from "@/lib/tauri-api";

export type Platform = "macos" | "windows" | "linux" | "unknown";

let cached: Platform | null = null;
let pending: Promise<Platform> | null = null;

function normalize(p: string): Platform {
  return p === "macos" || p === "windows" || p === "linux" ? p : "unknown";
}

export function usePlatform(): Platform {
  const [platform, setPlatform] = useState<Platform>(cached ?? "unknown");

  useEffect(() => {
    if (!IS_DESKTOP || cached) return;
    pending ??= desktopAPI.getPlatform().then((p) => {
      cached = normalize(p);
      return cached;
    });
    pending.then(setPlatform);
  }, []);

  return platform;
}

export function useIsMacOS(): boolean {
  return usePlatform() === "macos";
}

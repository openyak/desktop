"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Minus, Square, X, Copy } from "lucide-react";
import { IS_DESKTOP, TITLE_BAR_HEIGHT } from "@/lib/constants";
import { desktopAPI } from "@/lib/tauri-api";
import { useIsMacOS } from "@/hooks/use-platform";

function OpenYakLogo() {
  return (
    <Image
      src="/favicon.svg"
      width={18}
      height={18}
      alt="OpenYak"
      className="shrink-0"
      unoptimized
    />
  );
}

/**
 * Desktop window chrome.
 *
 * - macOS: renders only a transparent drag strip behind page headers
 *   (z below ChatHeader/Sidebar). Native traffic lights come from Tauri's
 *   overlay title bar style; page headers provide the visible content.
 * - Windows/Linux: full custom title bar with brand + min/max/close controls.
 */
export function TitleBar() {
  const [isMaximized, setIsMaximized] = useState(false);
  const isMac = useIsMacOS();
  const pathname = usePathname();

  useEffect(() => {
    if (!IS_DESKTOP || isMac) return;
    desktopAPI.isMaximized().then(setIsMaximized);
    const cleanup = desktopAPI.onMaximizeChange(setIsMaximized);
    return () => cleanup();
  }, [isMac]);

  if (!IS_DESKTOP) return null;

  if (isMac) {
    // Chat pages already have a ChatHeader that acts as the window drag
    // region, so we skip the strip there to avoid it blocking buttons.
    const isChatPage = pathname?.startsWith("/c/") ?? false;
    if (isChatPage) return null;

    return (
      <div
        data-tauri-drag-region
        className="fixed top-0 left-0 right-0 z-[5] select-none"
        style={{ height: TITLE_BAR_HEIGHT }}
        aria-hidden="true"
      />
    );
  }

  return (
    <div
      data-tauri-drag-region
      className="fixed top-0 left-0 right-0 z-50 flex items-center select-none"
      style={{
        height: TITLE_BAR_HEIGHT,
        backgroundColor: "var(--surface-primary)",
        borderBottom: "1px solid var(--border-primary)",
      }}
    >
      <div className="flex items-center gap-2 pl-3 h-full shrink-0">
        <OpenYakLogo />
        <span className="text-xs font-medium text-[var(--text-secondary)] tracking-wide">
          OpenYak
        </span>
      </div>

      <div data-tauri-drag-region className="flex-1 h-full" />

      <div className="flex items-center h-full shrink-0">
        <button
          onClick={() => desktopAPI.minimize()}
          className="inline-flex items-center justify-center w-[46px] h-full
                     text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)]
                     transition-colors"
          aria-label="Minimize"
        >
          <Minus className="h-4 w-4" />
        </button>
        <button
          onClick={() => desktopAPI.maximize()}
          className="inline-flex items-center justify-center w-[46px] h-full
                     text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)]
                     transition-colors"
          aria-label={isMaximized ? "Restore" : "Maximize"}
        >
          {isMaximized ? (
            <Copy className="h-3.5 w-3.5" />
          ) : (
            <Square className="h-3 w-3" />
          )}
        </button>
        <button
          onClick={() => desktopAPI.close()}
          className="inline-flex items-center justify-center w-[46px] h-full
                     text-[var(--text-secondary)] hover:bg-red-600 hover:text-white
                     transition-colors"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

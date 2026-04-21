"use client";

import { useIsMacOS } from "@/hooks/use-platform";
import { IS_DESKTOP } from "@/lib/constants";

/**
 * Empty strip at the top of the sidebar.
 *
 * Codex-style: no toggle/new-chat buttons here — those live in the chat
 * header so they stay accessible in both open and collapsed states. This
 * strip only exists to:
 *   - clear macOS native traffic lights
 *   - provide a drag region so the user can move the window from the
 *     sidebar's top area
 */
export function SidebarHeader() {
  const isMac = useIsMacOS();
  const macTopInset = IS_DESKTOP && isMac;

  return (
    <div
      data-tauri-drag-region
      aria-hidden="true"
      style={{ height: macTopInset ? 48 : 12 }}
    />
  );
}

"use client";

import { useEffect, useRef } from "react";
import { useSidebarStore } from "@/stores/sidebar-store";
import { SIDEBAR_MAX_WIDTH, SIDEBAR_MIN_WIDTH } from "@/lib/constants";

/**
 * 4px hit target on the sidebar's right edge. Drag left/right to resize.
 * Double-click resets to the default width. Width persists via sidebar store.
 */
export function SidebarResizeHandle() {
  const width = useSidebarStore((s) => s.width);
  const setWidth = useSidebarStore((s) => s.setWidth);
  const draggingRef = useRef(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!draggingRef.current) return;
      const delta = e.clientX - startXRef.current;
      const next = Math.max(
        SIDEBAR_MIN_WIDTH,
        Math.min(SIDEBAR_MAX_WIDTH, startWidthRef.current + delta),
      );
      setWidth(next);
    };
    const onUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [setWidth]);

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-valuemin={SIDEBAR_MIN_WIDTH}
      aria-valuemax={SIDEBAR_MAX_WIDTH}
      aria-valuenow={width}
      aria-label="Resize sidebar"
      className="group absolute inset-y-0 right-0 z-40 w-1 cursor-col-resize"
      onPointerDown={(e) => {
        e.preventDefault();
        draggingRef.current = true;
        startXRef.current = e.clientX;
        startWidthRef.current = width;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
      }}
      onDoubleClick={() => setWidth(300)}
    >
      <div className="absolute inset-y-0 right-0 w-px bg-transparent transition-colors group-hover:bg-[var(--border-heavy)]" />
    </div>
  );
}

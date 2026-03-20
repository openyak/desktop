"use client";

import { useCallback, useEffect, useRef } from "react";
import { MAX_INPUT_HEIGHT } from "@/lib/constants";

/**
 * Auto-resize a textarea to fit its content, up to a max height.
 */
export function useAutoResize() {
  const ref = useRef<HTMLTextAreaElement>(null);

  const resize = useCallback(() => {
    const textarea = ref.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_INPUT_HEIGHT)}px`;
  }, []);

  useEffect(() => {
    resize();
  }, [resize]);

  return { ref, resize };
}

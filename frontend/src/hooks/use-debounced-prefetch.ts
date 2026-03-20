"use client";

import { useCallback, useEffect, useRef } from "react";

/**
 * Hook for debounced prefetch operations
 * Delays execution until user stops hovering for specified delay
 * Prevents request storms from rapid hover events
 *
 * @param delay - Debounce delay in milliseconds (default: 300ms)
 * @returns Object with prefetch and cancel functions
 */
export function useDebouncedPrefetch(delay = 300) {
  const timeoutRef = useRef<NodeJS.Timeout>(undefined);

  const prefetch = useCallback(
    (fn: () => void) => {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(fn, delay);
    },
    [delay]
  );

  const cancel = useCallback(() => {
    clearTimeout(timeoutRef.current);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => clearTimeout(timeoutRef.current);
  }, []);

  return { prefetch, cancel };
}

"use client";

import { useEffect, useState, useRef } from "react";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";

/**
 * Top progress bar that animates during route transitions
 * Similar to YouTube/GitHub style loading indicator
 */
export function RouteProgressBar() {
  const pathname = usePathname();
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const prevPathnameRef = useRef(pathname);
  const timersRef = useRef<NodeJS.Timeout[]>([]);

  useEffect(() => {
    // Skip if pathname hasn't actually changed (initial mount)
    if (prevPathnameRef.current === pathname) {
      prevPathnameRef.current = pathname;
      return;
    }
    prevPathnameRef.current = pathname;

    // Clear any existing timers
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];

    // Start progress
    setIsLoading(true);
    setProgress(0);

    // Simulate loading progress with realistic timing
    timersRef.current.push(
      setTimeout(() => setProgress(20), 0),
      setTimeout(() => setProgress(40), 100),
      setTimeout(() => setProgress(70), 200),
      setTimeout(() => setProgress(90), 350),
      setTimeout(() => {
        setProgress(100);
        setTimeout(() => setIsLoading(false), 200);
      }, 500)
    );

    return () => {
      timersRef.current.forEach(clearTimeout);
    };
  }, [pathname]);

  return (
    <AnimatePresence>
      {isLoading && (
        <motion.div
          className="fixed top-0 left-0 right-0 z-50 h-[2px] bg-gradient-to-r from-[var(--brand-primary)] via-[var(--brand-primary)]/80 to-[var(--brand-primary)]/60"
          initial={{ width: "0%", opacity: 1 }}
          animate={{
            width: `${progress}%`,
            opacity: progress === 100 ? 0 : 1
          }}
          exit={{ opacity: 0 }}
          transition={{
            width: { duration: 0.3, ease: "easeOut" },
            opacity: { duration: 0.2 }
          }}
          style={{
            boxShadow: "0 0 8px var(--brand-primary), 0 0 4px var(--brand-primary)",
          }}
        />
      )}
    </AnimatePresence>
  );
}

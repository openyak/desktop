"use client";

import { useState, useRef, useCallback, type ReactNode } from "react";
import { Loader2, ArrowDown } from "lucide-react";

const PULL_THRESHOLD = 80;
const MAX_PULL = 120;

interface PullToRefreshProps {
  onRefresh: () => Promise<void>;
  children: ReactNode;
}

/**
 * Pull-to-refresh wrapper for mobile scroll containers.
 *
 * Works by intercepting touch events at the top of a scrollable area.
 * When the user pulls down past the threshold, triggers onRefresh.
 */
export function PullToRefresh({ onRefresh, children }: PullToRefreshProps) {
  const [pullDistance, setPullDistance] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const touchStartY = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pulling = useRef(false);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (refreshing) return;
    const scrollTop = scrollRef.current?.scrollTop ?? 0;
    if (scrollTop <= 0) {
      touchStartY.current = e.touches[0].clientY;
      pulling.current = true;
    }
  }, [refreshing]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!pulling.current || refreshing) return;
    const scrollTop = scrollRef.current?.scrollTop ?? 0;
    if (scrollTop > 0) {
      pulling.current = false;
      setPullDistance(0);
      return;
    }
    const delta = e.touches[0].clientY - touchStartY.current;
    if (delta > 0) {
      // Dampened pull distance
      const dampened = Math.min(delta * 0.5, MAX_PULL);
      setPullDistance(dampened);
    }
  }, [refreshing]);

  const handleTouchEnd = useCallback(async () => {
    if (!pulling.current || refreshing) return;
    pulling.current = false;
    if (pullDistance >= PULL_THRESHOLD) {
      setRefreshing(true);
      setPullDistance(PULL_THRESHOLD * 0.6);
      try {
        await onRefresh();
      } finally {
        setRefreshing(false);
        setPullDistance(0);
      }
    } else {
      setPullDistance(0);
    }
  }, [pullDistance, refreshing, onRefresh]);

  const progress = Math.min(pullDistance / PULL_THRESHOLD, 1);
  const showIndicator = pullDistance > 10 || refreshing;

  return (
    <div className="relative flex-1 overflow-hidden">
      {/* Pull indicator */}
      {showIndicator && (
        <div
          className="absolute inset-x-0 top-0 z-10 flex items-center justify-center pointer-events-none transition-opacity"
          style={{ height: Math.max(pullDistance, refreshing ? 48 : 0) }}
        >
          {refreshing ? (
            <Loader2 className="h-5 w-5 animate-spin text-[var(--text-tertiary)]" />
          ) : (
            <ArrowDown
              className="h-5 w-5 text-[var(--text-tertiary)] transition-transform"
              style={{
                transform: `rotate(${progress >= 1 ? 180 : 0}deg)`,
                opacity: progress,
              }}
            />
          )}
        </div>
      )}

      {/* Scrollable content */}
      <div
        ref={scrollRef}
        className="flex-1 h-full overflow-y-auto"
        style={{
          transform: showIndicator ? `translateY(${pullDistance}px)` : undefined,
          transition: pulling.current ? "none" : "transform 0.3s ease-out",
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {children}
      </div>
    </div>
  );
}

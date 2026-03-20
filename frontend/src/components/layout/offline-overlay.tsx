"use client";

import { WifiOff, RefreshCw } from "lucide-react";
import { useConnectionStore } from "@/stores/connection-store";
import { Button } from "@/components/ui/button";

export function OfflineOverlay() {
  const status = useConnectionStore((s) => s.status);

  // Only show when fully disconnected, not during brief reconnection attempts
  if (status !== "disconnected") return null;

  const handleRetry = () => {
    // Trigger a reconnection attempt
    window.location.reload();
  };

  return (
    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[var(--surface-chat)]/90 backdrop-blur-sm">
      <WifiOff className="h-10 w-10 text-[var(--text-tertiary)] mb-4" />
      <h2 className="text-lg font-medium text-[var(--text-primary)] mb-1">
        Unable to connect
      </h2>
      <p className="text-sm text-[var(--text-secondary)] text-center max-w-xs mb-6">
        Make sure the backend server is running and try again.
      </p>
      <Button variant="outline" size="sm" onClick={handleRetry}>
        <RefreshCw className="h-4 w-4 mr-2" />
        Retry connection
      </Button>
    </div>
  );
}

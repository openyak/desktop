"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000, // 60 seconds - increased from 30s for better caching
            gcTime: 5 * 60 * 1000, // 5 minutes - retain frequently accessed data
            retry: 1,
            refetchOnWindowFocus: false,
            structuralSharing: true, // Prevent unnecessary re-renders
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

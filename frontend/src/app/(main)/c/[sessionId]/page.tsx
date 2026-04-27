import { Suspense } from "react";
import { SessionPageClient } from "./session-page-client";
import { resolveSessionId } from "@/lib/routes";

/**
 * Required for Next.js static export — dynamic routes need this.
 * Returning at least one entry prevents Next.js from failing to detect the function.
 * Actual sessions are resolved client-side via useParams in the Electron app.
 */
export async function generateStaticParams() {
  return [{ sessionId: "_" }];
}

interface SessionPageProps {
  params: Promise<{ sessionId?: string }>;
  searchParams?: Promise<{ sessionId?: string | string[] }>;
}

export default async function SessionPage({ params, searchParams }: SessionPageProps) {
  const resolvedParams = await params;
  const resolvedSearchParams = await searchParams;
  const querySessionId = Array.isArray(resolvedSearchParams?.sessionId)
    ? resolvedSearchParams.sessionId[0]
    : resolvedSearchParams?.sessionId;
  const sessionId = resolveSessionId(resolvedParams.sessionId ?? null, querySessionId ?? null);

  return (
    <Suspense fallback={null}>
      <SessionPageClient sessionId={sessionId} />
    </Suspense>
  );
}

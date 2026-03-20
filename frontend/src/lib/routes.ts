const IS_DESKTOP_BUILD = process.env.NEXT_PUBLIC_DESKTOP_BUILD === "true";

export function getChatRoute(sessionId?: string | null): string {
  if (!sessionId) return "/c/new";
  return IS_DESKTOP_BUILD
    ? `/c/_?sessionId=${encodeURIComponent(sessionId)}`
    : `/c/${sessionId}`;
}

export function resolveSessionId(
  pathSessionId?: string | null,
  querySessionId?: string | null,
): string | null {
  if (!pathSessionId) return querySessionId ?? null;
  if (pathSessionId === "_") return querySessionId ?? null;
  return pathSessionId;
}

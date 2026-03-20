/**
 * Direct API client for the OpenYak Cloud Proxy.
 *
 * Auth and billing calls go directly to the proxy server,
 * not through the local backend.
 */

import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import { API } from "@/lib/constants";

class ProxyApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: unknown,
  ) {
    super(`Proxy API ${status}: ${statusText}`);
    this.name = "ProxyApiError";
  }
}

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(proxyUrl: string, refreshToken: string): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${proxyUrl}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return null;

      const data = (await res.json()) as {
        access_token: string;
        refresh_token: string;
      };

      const current = useAuthStore.getState();
      useAuthStore.setState({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isConnected: current.isConnected,
      });

      if (current.isConnected) {
        try {
          await api.post(API.CONFIG.OPENYAK_ACCOUNT, {
            proxy_url: proxyUrl,
            token: data.access_token,
            refresh_token: data.refresh_token,
          });
        } catch {
          // Keep local auth usable even if backend token sync fails.
        }
      }

      return data.access_token;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

async function parseError(res: Response): Promise<ProxyApiError> {
  const raw = await res.text();
  let body: unknown;
  try {
    body = JSON.parse(raw);
  } catch {
    body = raw;
  }
  return new ProxyApiError(res.status, res.statusText, body);
}

async function proxyRequest<T>(
  path: string,
  options?: RequestInit & { noAuth?: boolean },
): Promise<T> {
  const { proxyUrl, accessToken, refreshToken } = useAuthStore.getState();
  if (!proxyUrl) throw new Error("Proxy URL not configured");

  const buildHeaders = (token: string | null): Record<string, string> => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options?.headers as Record<string, string>),
    };
    if (!options?.noAuth && token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  };

  let res = await fetch(`${proxyUrl}${path}`, {
    ...options,
    headers: buildHeaders(accessToken || null),
  });

  if (res.status === 401 && !options?.noAuth && refreshToken) {
    const refreshedAccess = await refreshAccessToken(proxyUrl, refreshToken);
    if (refreshedAccess) {
      res = await fetch(`${proxyUrl}${path}`, {
        ...options,
        headers: buildHeaders(refreshedAccess),
      });
    } else {
      useAuthStore.getState().logout();
    }
  }

  if (!res.ok) {
    throw await parseError(res);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/**
 * Auth API — called directly on the proxy (before account is connected).
 * These use a specific proxyUrl parameter instead of reading from store.
 */
async function authRequest<T>(
  proxyUrl: string,
  path: string,
  body: unknown,
): Promise<T> {
  const res = await fetch(`${proxyUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const raw = await res.text();
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = raw;
    }
    throw new ProxyApiError(res.status, res.statusText, parsed);
  }

  return res.json() as Promise<T>;
}

export const proxyApi = {
  get: <T>(path: string) => proxyRequest<T>(path),

  post: <T>(path: string, data?: unknown) =>
    proxyRequest<T>(path, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }),

  authPost: <T>(proxyUrl: string, path: string, data: unknown) =>
    authRequest<T>(proxyUrl, path, data),
};

export { ProxyApiError };

"""Private Network Access support for desktop loopback API calls."""

from __future__ import annotations

from collections.abc import Iterable

from app.auth.csrf import _origin_allowed, _runtime_origins


class PrivateNetworkAccessMiddleware:
    """Add the PNA opt-in header for trusted browser preflights.

    Chromium/WebView2 can send ``Access-Control-Request-Private-Network``
    when the Tauri frontend calls the loopback backend. Starlette's CORS
    middleware does not emit ``Access-Control-Allow-Private-Network``, so
    otherwise the browser may block the actual request before it reaches
    the authenticated API. We only add the header for origins that already
    pass OpenYak's Origin allowlist.
    """

    def __init__(self, app, *, extra_allowed_origins: Iterable[str] = ()):
        self.app = app
        self._extra = tuple(
            o.rstrip("/") for o in (s.strip() for s in extra_allowed_origins) if o
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        add_pna_header = self._should_add_header(scope)

        async def send_with_pna(message):
            if add_pna_header and message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                if not any(k.lower() == b"access-control-allow-private-network" for k, _ in headers):
                    headers.append([b"access-control-allow-private-network", b"true"])
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_pna)

    def _should_add_header(self, scope) -> bool:
        if scope.get("method", "").upper() != "OPTIONS":
            return False

        headers = dict(scope.get("headers", []))
        requested = headers.get(b"access-control-request-private-network", b"")
        if requested.lower() != b"true":
            return False

        origin = headers.get(b"origin", b"").decode("latin-1", errors="replace").strip()
        if not origin or origin == "null":
            return False

        return _origin_allowed(origin, self._extra, _runtime_origins(scope))

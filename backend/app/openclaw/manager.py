"""OpenClaw process manager — install, start, stop, health-check.

Follows the same pattern as OllamaManager: manages a child process,
provides download/setup as an async iterator for SSE progress, and
exposes status for the frontend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)

_HEALTH_RETRIES = 30
_HEALTH_INTERVAL = 1.0  # seconds between health checks
_DEFAULT_PORT = 18789


def _is_port_free(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _find_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class OpenClawManager:
    """Manages the OpenClaw gateway binary and process lifecycle."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.openclaw_dir = self.data_dir / "openclaw"
        self._process: subprocess.Popen | None = None
        self._port: int = _DEFAULT_PORT
        self._token: str = ""
        self._npx_mode: bool = False  # True if using npx instead of local binary

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def mjs_path(self) -> Path:
        """Absolute path to the openclaw.mjs entry point (avoids .cmd shim issues)."""
        return (self.openclaw_dir / "node_modules" / "openclaw" / "openclaw.mjs").resolve()

    @property
    def is_installed(self) -> bool:
        """Check if OpenClaw is available (local install or system PATH)."""
        if self.mjs_path.exists():
            return True
        return shutil.which("openclaw") is not None

    @property
    def is_running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._port}"

    @property
    def ws_url(self) -> str:
        return f"ws://127.0.0.1:{self._port}"

    @property
    def token(self) -> str:
        return self._token

    # ------------------------------------------------------------------
    # Node.js resolution (OpenClaw needs Node 22.12+)
    # ------------------------------------------------------------------

    def _find_node22(self) -> tuple[str | None, str | None]:
        """Find Node 22+ binary and its npm.

        Search order:
          1. Bundled Node.js in OPENYAK_RESOURCE_DIR/nodejs/
          2. System PATH
          3. nvm-windows (NVM_HOME) / nvm (NVM_DIR)
          4. fnm (~/.fnm) / volta (~/.volta)
        """
        # 1. Bundled Node (highest priority — works on any user machine)
        resource_dir = os.environ.get("OPENYAK_RESOURCE_DIR")
        if resource_dir:
            bundled = self._probe_node_dir(Path(resource_dir) / "nodejs")
            if bundled:
                return bundled

        # 2. System PATH
        node = shutil.which("node")
        npm = shutil.which("npm")
        if node and self._check_node_version(node):
            return node, npm

        # 3. nvm-windows / nvm
        nvm_home = os.environ.get("NVM_HOME") or os.environ.get("NVM_DIR")
        if nvm_home:
            nvm_path = Path(nvm_home)
            search_dirs = list(nvm_path.glob("v22.*")) + list(
                (nvm_path / "versions" / "node").glob("v22.*")
            )
            search_dirs.sort(key=lambda p: p.name, reverse=True)
            for d in search_dirs:
                result = self._probe_node_dir(d)
                if result:
                    return result

        # 4. fnm
        fnm_dir = Path.home() / ".fnm" / "node-versions"
        if fnm_dir.exists():
            for d in sorted(fnm_dir.glob("v22.*"), reverse=True):
                result = self._probe_node_dir(d / "installation")
                if result:
                    return result

        # 5. volta
        volta_dir = Path.home() / ".volta" / "tools" / "image" / "node"
        if volta_dir.exists():
            for d in sorted(volta_dir.glob("22.*"), reverse=True):
                result = self._probe_node_dir(d)
                if result:
                    return result

        return None, None

    def _probe_node_dir(self, d: Path) -> tuple[str, str | None] | None:
        """Check if a directory contains a valid Node 22+ binary. Returns (node, npm) or None."""
        candidates = [d / "node.exe", d / "node", d / "bin" / "node"]
        for c in candidates:
            if c.exists() and self._check_node_version(str(c)):
                npm_candidates = [
                    c.parent / "npm.cmd", c.parent / "npm",
                    c.parent / "npm.exe",
                ]
                found_npm = next((str(n) for n in npm_candidates if n.exists()), None)
                return str(c), found_npm
        return None

    @staticmethod
    def _check_node_version(node_path: str) -> bool:
        """Return True if node at path is v22.12+."""
        try:
            result = subprocess.run(
                [node_path, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            ver = result.stdout.strip().lstrip("v")
            parts = ver.split(".")
            major, minor = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            return major > 22 or (major == 22 and minor >= 12)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Install
    # ------------------------------------------------------------------

    async def install(self) -> AsyncIterator[dict[str, Any]]:
        """Install OpenClaw via npm. Yields progress events for SSE streaming."""

        node, npm = self._find_node22()
        if not node or not npm:
            yield {
                "status": "error",
                "message": "Node.js 22.12+ required. Install via: nvm install 22 && nvm use 22",
            }
            return

        yield {"status": "installing", "message": "Installing OpenClaw via npm..."}

        # Create local install directory
        self.openclaw_dir.mkdir(parents=True, exist_ok=True)

        # Initialize package.json if needed
        pkg_json = self.openclaw_dir / "package.json"
        if not pkg_json.exists():
            pkg_json.write_text(json.dumps({"name": "openclaw-local", "private": True}))

        # Build env with the correct Node in PATH so npm uses node22
        env = {**dict(os.environ)}
        node_dir = str(Path(node).parent)
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")

        # npm install openclaw
        try:
            proc = await asyncio.create_subprocess_exec(
                npm, "install", "openclaw@latest",
                cwd=str(self.openclaw_dir),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode().strip()
                if text:
                    yield {"status": "installing", "message": text}

            await proc.wait()

            if proc.returncode != 0:
                stderr = (await proc.stderr.read()).decode()
                yield {"status": "error", "message": f"npm install failed: {stderr[:500]}"}
                return

        except Exception as e:
            yield {"status": "error", "message": f"Installation failed: {e}"}
            return

        if not self.binary_path.exists():
            yield {"status": "error", "message": "Installation completed but binary not found."}
            return

        yield {"status": "done", "message": "OpenClaw installed successfully."}

    # ------------------------------------------------------------------
    # OpenYak provider config
    # ------------------------------------------------------------------

    def _write_openyak_provider_config(self, openyak_port: int = 8000) -> None:
        """Write/merge OpenYak as an AI provider into ~/.openclaw/openclaw.json.

        This makes OpenClaw use OpenYak's /v1/chat/completions for AI responses
        when handling messages from WhatsApp, Discord, etc.
        """
        config_path = Path.home() / ".openclaw" / "openclaw.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or start fresh
        existing: dict = {}
        if config_path.exists():
            try:
                existing = json.loads(config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        # Merge OpenYak provider
        models = existing.setdefault("models", {})
        models["mode"] = "merge"
        providers = models.setdefault("providers", {})
        providers["openyak"] = {
            "baseUrl": f"http://127.0.0.1:{openyak_port}/v1",
            "api": "openai-completions",
            "models": [
                {
                    "id": "openyak-build",
                    "name": "OpenYak Build (full agent with tools)",
                    "reasoning": False,
                    "input": ["text"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                    "contextWindow": 128000,
                    "maxTokens": 32000,
                },
                {
                    "id": "openyak-general",
                    "name": "OpenYak General",
                    "reasoning": False,
                    "input": ["text"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                    "contextWindow": 128000,
                    "maxTokens": 32000,
                },
            ],
        }

        # Set OpenYak as the default model
        agents = existing.setdefault("agents", {})
        defaults = agents.setdefault("defaults", {})
        model = defaults.setdefault("model", {})
        model["primary"] = "openyak/openyak-build"

        config_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Wrote OpenYak provider config to %s", config_path)

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    async def start(self, token: str = "", openyak_port: int = 8000) -> str:
        """Start the OpenClaw gateway process. Returns the WebSocket URL."""
        if self.is_running:
            return self.ws_url

        # Clean up any orphaned gateway processes from previous runs
        await self._kill_port_listeners(self._port)

        # Resolve openclaw — prefer running node + .mjs directly to avoid .cmd shim issues
        node, _ = self._find_node22()
        if not node:
            raise RuntimeError("Node.js 22.12+ required to run OpenClaw.")

        if self.mjs_path.exists():
            cmd_prefix = [node, str(self.mjs_path)]
        else:
            system_bin = shutil.which("openclaw")
            if not system_bin:
                raise RuntimeError("OpenClaw not installed. Run setup first.")
            cmd_prefix = [system_bin]

        # Find port
        if _is_port_free(self._port):
            port = self._port
        else:
            port = _find_free_port()
        self._port = port

        # Generate token if not provided
        if not token:
            import secrets
            token = secrets.token_urlsafe(32)
        self._token = token

        # Prepare environment
        env = {**dict(os.environ), "OPENCLAW_GATEWAY_TOKEN": token}

        # Write OpenYak as the AI provider so OpenClaw routes messages to us
        self._write_openyak_provider_config(openyak_port)

        # Ensure openclaw config directory exists
        config_dir = Path.home() / ".openclaw"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Start process
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

        try:
            self._process = subprocess.Popen(
                [*cmd_prefix, "gateway", "run", "--port", str(port), "--auth", "none", "--allow-unconfigured", "--verbose"],
                env=env,
                stdout=open(str(config_dir / "gateway.log"), "w"),
                stderr=subprocess.STDOUT,
                cwd=str(config_dir),
                creationflags=creation_flags,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start OpenClaw: {e}")

        # Wait for health
        await self._wait_for_health()

        logger.info("OpenClaw gateway started on port %d (pid=%d)", port, self._process.pid)
        return self.ws_url

    async def stop(self) -> None:
        """Stop the OpenClaw gateway process and any orphaned processes on the port."""
        if self._process is not None:
            pid = self._process.pid
            logger.info("Stopping OpenClaw (pid=%d)...", pid)
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        capture_output=True, timeout=10,
                    )
                else:
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
            except Exception as e:
                logger.warning("Error stopping OpenClaw: %s", e)
            self._process = None

        # Kill any orphaned processes listening on our port (prevents ghost instances)
        await self._kill_port_listeners(self._port)

    @staticmethod
    async def _kill_port_listeners(port: int) -> None:
        """Kill any process listening on the given port (cleanup orphaned gateways)."""
        if sys.platform == "win32":
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["netstat", "-ano"],
                    capture_output=True, text=True, timeout=5,
                )
                import re as _re
                for line in result.stdout.splitlines():
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]
                        if pid.isdigit() and int(pid) > 0:
                            logger.info("Killing orphaned process on port %d (pid=%s)", port, pid)
                            subprocess.run(
                                ["taskkill", "/PID", pid, "/T", "/F"],
                                capture_output=True, timeout=5,
                            )
            except Exception as e:
                logger.debug("Port cleanup failed: %s", e)
        else:
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True, text=True, timeout=5,
                )
                for pid in result.stdout.strip().split():
                    if pid.isdigit():
                        logger.info("Killing orphaned process on port %d (pid=%s)", port, pid)
                        os.kill(int(pid), 9)
            except Exception as e:
                logger.debug("Port cleanup failed: %s", e)

    async def _wait_for_health(self) -> None:
        """Poll until the gateway is responsive."""
        url = f"{self.base_url}/health"
        async with httpx.AsyncClient(timeout=3.0) as client:
            for i in range(_HEALTH_RETRIES):
                try:
                    resp = await client.get(url)
                    if resp.status_code < 500:
                        logger.info("OpenClaw health check passed (attempt %d/%d)", i + 1, _HEALTH_RETRIES)
                        return
                except httpx.HTTPError:
                    pass

                # Check process didn't crash
                if self._process and self._process.poll() is not None:
                    raise RuntimeError(f"OpenClaw exited with code {self._process.returncode}")

                await asyncio.sleep(_HEALTH_INTERVAL)

        raise RuntimeError(f"OpenClaw not ready after {_HEALTH_RETRIES}s")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def status(self) -> dict[str, Any]:
        """Return status for the API."""
        return {
            "installed": self.is_installed,
            "running": self.is_running,
            "port": self._port,
            "ws_url": self.ws_url if self.is_running else None,
            "token": self._token if self.is_running else None,
        }

    # ------------------------------------------------------------------
    # CLI command runner (for channels add/login/remove)
    # ------------------------------------------------------------------

    def _build_cmd_prefix(self) -> list[str]:
        """Build the [node, mjs] or [openclaw] command prefix."""
        node, _ = self._find_node22()
        if not node:
            raise RuntimeError("Node.js 22.12+ required.")
        if self.mjs_path.exists():
            return [node, str(self.mjs_path)]
        system_bin = shutil.which("openclaw")
        if system_bin:
            return [system_bin]
        raise RuntimeError("OpenClaw not installed.")

    async def run_cli(self, args: list[str], timeout: float = 120) -> dict[str, Any]:
        """Run an openclaw CLI command and return {ok, stdout, stderr}."""
        try:
            cmd = [*self._build_cmd_prefix(), *args]
        except Exception as e:
            logger.error("Failed to build CLI command: %s", e)
            return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}

        logger.info("Running CLI: %s", " ".join(cmd))
        try:
            # Use subprocess.run in a thread — asyncio.create_subprocess_exec can
            # have issues on Windows with uvicorn's event loop policy.
            import subprocess as _sp
            result = await asyncio.to_thread(
                _sp.run, cmd,
                capture_output=True, timeout=timeout,
            )
            out = {
                "ok": result.returncode == 0,
                "stdout": result.stdout.decode(errors="replace"),
                "stderr": result.stderr.decode(errors="replace"),
                "returncode": result.returncode,
            }
            logger.info("CLI result: ok=%s rc=%d stdout=%.100s stderr=%.100s",
                        out["ok"], result.returncode,
                        out["stdout"], out["stderr"])
            return out
        except _sp.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "Command timed out", "returncode": -1}
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}

    async def run_cli_stream(self, args: list[str], timeout: float = 180) -> AsyncIterator[str]:
        """Run an openclaw CLI command and yield stdout lines in real time."""
        import subprocess as _sp
        import queue
        import threading

        try:
            cmd = [*self._build_cmd_prefix(), *args]
        except Exception as e:
            yield f"[error] {e}"
            return

        logger.info("Streaming CLI: %s", " ".join(cmd))

        # Use a thread + queue to read lines without blocking the event loop
        q: queue.Queue[str | None] = queue.Queue()

        def _reader(proc: _sp.Popen) -> None:
            try:
                assert proc.stdout is not None
                for raw in proc.stdout:
                    q.put(raw.decode(errors="replace").rstrip("\n"))
            except Exception:
                pass
            finally:
                q.put(None)  # sentinel

        # Force Node.js to flush stdout on every write (avoids block buffering in pipes)
        env = {**os.environ}
        env["NODE_OPTIONS"] = env.get("NODE_OPTIONS", "") + " --max-old-space-size=4096"
        # Disable Node.js stdout buffering via env
        env["NODE_NO_READLINE"] = "1"

        proc = _sp.Popen(
            cmd,
            stdout=_sp.PIPE,
            stderr=_sp.PIPE,
            env=env,
        )
        t = threading.Thread(target=_reader, args=(proc,), daemon=True)
        t.start()

        deadline = asyncio.get_event_loop().time() + timeout
        try:
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    yield "[timeout]"
                    break
                try:
                    line = await asyncio.to_thread(q.get, True, min(remaining, 2.0))
                except Exception:
                    continue
                if line is None:
                    break
                yield line
        finally:
            # Don't terminate immediately — give process a moment to finish
            try:
                proc.wait(timeout=3)
            except _sp.TimeoutExpired:
                proc.terminate()
            t.join(timeout=5)

        if proc.returncode is None:
            proc.kill()
            proc.wait()

        # Read any remaining buffered stdout after process exits
        if proc.stdout:
            remaining_out = proc.stdout.read()
            if remaining_out:
                for line in remaining_out.decode(errors="replace").splitlines():
                    if line.strip():
                        yield line.strip()

        # Signal success/failure based on exit code
        if proc.returncode == 0:
            yield "[exit:0]"
        elif proc.returncode and proc.returncode != 0:
            stderr_out = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
            if stderr_out.strip():
                yield f"[error] {stderr_out.strip()}"

    async def uninstall(self) -> dict[str, Any]:
        """Remove the local OpenClaw installation."""
        if self.is_running:
            await self.stop()

        removed = False
        if self.openclaw_dir.exists():
            shutil.rmtree(self.openclaw_dir, ignore_errors=True)
            removed = True

        return {"removed": removed}

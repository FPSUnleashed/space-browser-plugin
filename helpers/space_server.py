"""Manages Space Agent server lifecycle - start, stop, health check."""

import asyncio
import os
import subprocess
import time
from functools import partial
from typing import Optional

import requests

# Track the server subprocess globally so we can clean up
_server_process: Optional[subprocess.Popen] = None


def _find_space_agent_dir(custom_path: str = "") -> Optional[str]:
    """Find the Space Agent installation directory."""
    if custom_path and os.path.isdir(custom_path):
        for name in ("space.js", "space"):
            candidate = os.path.join(custom_path, name)
            if os.path.isfile(candidate):
                return custom_path

    # Check known locations
    search_paths = [
        "/a0/usr/projects/space_agent_plugin/space-agent",
        os.path.expanduser("~/space-agent"),
        os.path.expanduser("~/projects/space-agent"),
    ]

    for search_path in search_paths:
        if os.path.isdir(search_path):
            for name in ("space.js", "space"):
                candidate = os.path.join(search_path, name)
                if os.path.isfile(candidate):
                    return search_path

    return None


def _is_process_running(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _health_check_sync(url: str, timeout: float = 5.0) -> bool:
    """Check if Space Agent server is responding (sync)."""
    try:
        resp = requests.get(f"{url}/api/health", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def _ensure_server_running_sync(
    space_agent_path: str = "",
    port: int = 3000,
    timeout: float = 30.0,
) -> str:
    """Ensure Space Agent server is running, start it if needed (sync)."""
    global _server_process

    url = f"http://localhost:{port}"

    # Check if already running
    if _health_check_sync(url):
        return url

    # If we have a tracked process that died, clean up
    if _server_process is not None:
        if not _is_process_running(_server_process.pid):
            _server_process = None

    # Find the Space Agent installation directory
    agent_dir = _find_space_agent_dir(space_agent_path)
    if not agent_dir:
        raise RuntimeError(
            "Space Agent not found. Install it or set space_agent_path in plugin config. "
            "Searched: custom path, ~/space-agent, ~/projects/space-agent, "
            "/a0/usr/projects/space_agent_plugin/space-agent"
        )

    # Start the server
    env = os.environ.copy()
    env["SINGLE_USER_APP"] = "true"
    env["PORT"] = str(port)

    cmd = ["node", "space.js", "serve"]
    _server_process = subprocess.Popen(
        cmd,
        cwd=agent_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    )

    # Wait for health check to pass
    start_time = time.time()
    while time.time() - start_time < timeout:
        if _health_check_sync(url, timeout=2.0):
            return url
        # Check if process died
        if _server_process.poll() is not None:
            stderr_output = (
                _server_process.stderr.read().decode("utf-8", errors="replace")
                if _server_process.stderr
                else ""
            )
            raise RuntimeError(
                f"Space Agent server failed to start. "
                f"Exit code: {_server_process.returncode}.\n{stderr_output}"
            )
        time.sleep(1.0)

    raise TimeoutError(f"Space Agent server did not become healthy within {timeout}s")


async def ensure_server_running(
    space_agent_path: str = "",
    port: int = 3000,
    timeout: float = 30.0,
) -> str:
    """Async wrapper for ensure_server_running."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(
            _ensure_server_running_sync,
            space_agent_path=space_agent_path,
            port=port,
            timeout=timeout,
        ),
    )


def stop_server() -> None:
    """Stop the tracked server subprocess if running."""
    global _server_process
    if _server_process is not None:
        try:
            _server_process.terminate()
            try:
                _server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _server_process.kill()
                _server_process.wait(timeout=3)
        except Exception:
            pass
        finally:
            _server_process = None

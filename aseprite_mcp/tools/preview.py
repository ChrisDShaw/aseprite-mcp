import os
import subprocess
import sys
import tempfile
import signal
from .. import mcp


def _pid_path(port: int, host: str = "127.0.0.1") -> str:
    host_name = host.replace(":", "_")
    return os.path.join(tempfile.gettempdir(), f"aseprite_mcp_preview_{port}_{host_name}.pid")


def _normalize_host(host: str | None, allow_external: bool) -> str:
    value = (host or "127.0.0.1").strip() or "127.0.0.1"
    if allow_external:
        return value
    return "127.0.0.1"


def _pid_is_running(pid: int) -> bool:
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                check=False,
                capture_output=True,
                text=True
            )
            return str(pid) in result.stdout
        os.kill(pid, 0)
        return True
    except Exception:
        return False


@mcp.tool()
async def start_preview_server(
    directory: str,
    port: int = 8000,
    host: str = "127.0.0.1",
    allow_external: bool = False,
) -> str:
    """Start a simple HTTP server to preview exported sprites.

    By default the preview is bound to localhost only. To expose it outside the
    current machine, callers must explicitly set allow_external=True and choose a
    bind host such as 0.0.0.0.

    Args:
        directory: Directory to serve
        port: Port to bind (default 8000)
        host: Bind address for the preview server (default 127.0.0.1)
        allow_external: Allow the server to listen on a non-loopback interface
    """
    if not os.path.isdir(directory):
        return f"Directory {directory} not found"

    # Keep local previewing as the safe default; remote access is explicit.
    bind_host = _normalize_host(host, allow_external)
    if not allow_external and host and host.strip() not in ("", "127.0.0.1", "localhost"):
        return (
            "Refusing to bind preview server to a non-local address unless "
            "allow_external=True is explicitly set."
        )

    directory = os.path.abspath(directory)
    pid_file = _pid_path(port, bind_host)
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            if _pid_is_running(pid):
                return f"Preview server may already be running on port {port}"
        except Exception:
            pass
        os.remove(pid_file)

    args = [sys.executable, "-m", "http.server", str(port), "--bind", bind_host, "--directory", directory]
    popen_kwargs = {"cwd": directory, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        popen_kwargs["start_new_session"] = True
    proc = subprocess.Popen(args, **popen_kwargs)
    with open(pid_file, "w", encoding="utf-8") as f:
        f.write(str(proc.pid))

    if bind_host in ("0.0.0.0", "::"):
        url = f"http://localhost:{port}/"
    else:
        url = f"http://{bind_host}:{port}/"
    return f"Preview server started: {url}"


@mcp.tool()
async def stop_preview_server(port: int = 8000, host: str = "127.0.0.1") -> str:
    """Stop the preview HTTP server for a given port.

    Args:
        port: Port to stop (default 8000)
        host: Bind address used when starting the server (default 127.0.0.1)
    """
    bind_host = _normalize_host(host, allow_external=True)
    pid_file = _pid_path(port, bind_host)
    if not os.path.exists(pid_file):
        return f"No preview server PID found for port {port}"

    with open(pid_file, "r", encoding="utf-8") as f:
        pid = int(f.read().strip())

    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
    finally:
        os.remove(pid_file)

    return f"Preview server stopped on port {port}"

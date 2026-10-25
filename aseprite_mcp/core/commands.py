import os
import re
import subprocess
import tempfile
import threading

_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def _load_env_file(path: str) -> None:
    """Load simple KEY=VALUE settings without replacing existing environment values."""
    try:
        with open(path, encoding="utf-8") as env_file:
            lines = env_file.readlines()
    except FileNotFoundError:
        return

    for line in lines:
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        if entry.startswith("export "):
            entry = entry[7:].lstrip()
        key, separator, value = entry.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        if key in os.environ:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        os.environ[key] = value


_load_env_file(_ENV_PATH)

_MAX_LUA_SCRIPT_BYTES = int(os.getenv("ASEPRITE_MCP_MAX_LUA_BYTES", "65536"))
_LUA_TIMEOUT_SECONDS = float(os.getenv("ASEPRITE_MCP_LUA_TIMEOUT_SECONDS", "120"))
_MAX_COMMAND_OUTPUT_BYTES = int(os.getenv("ASEPRITE_MCP_MAX_OUTPUT_BYTES", "1048576"))
_UNSAFE_LUA_PATTERNS = re.compile(
    r"\b(?:dofile|loadfile|load|loadstring|require)\b"
    r"|\b(?:package|os|io|debug|jit)\s*\."
)


def lua_escape(s: str) -> str:
    """Escape a string for safe embedding inside a Lua double-quoted string literal."""
    return (
        s.replace("\\", "\\\\")
         .replace('"', '\\"')
         .replace("\n", "\\n")
         .replace("\r", "\\r")
         .replace("\0", "\\0")
    )


def reject_traversal(path: str) -> str | None:
    """Reject parent-directory traversal in a user-supplied path.

    Returns an error message string when the path contains a `..`
    component, or None when the path looks safe.

    The check works on normalized path components, so it does not
    false-positive on filenames like `foo..bar.aseprite` (the previous
    `'..' in path` substring check did). Absolute paths and tilde
    expansion are not rejected here: this function targets traversal
    only, not access scoping.
    """
    parts = os.path.normpath(path).replace("\\", "/").split("/")
    if ".." in parts:
        return "Invalid filename: parent directory traversal not allowed"
    return None


def validate_lua_script(script_content: str, *, allow_unsafe_lua: bool = False, max_bytes: int = _MAX_LUA_SCRIPT_BYTES) -> str | None:
    """Apply size limits and a best-effort check for common host APIs.

    The text check is not a security boundary: Lua can access APIs indirectly
    or construct their names dynamically. Use OS-level isolation for untrusted
    scripts. Set allow_unsafe_lua=True or ASEPRITE_MCP_ALLOW_UNSAFE_LUA=1 only
    when trusted scripts need host-level Lua features.
    """
    if not script_content or not script_content.strip():
        return "Script cannot be empty"

    if max_bytes <= 0:
        return "Maximum script size must be greater than zero"
    max_bytes = min(max_bytes, _MAX_LUA_SCRIPT_BYTES)
    script_bytes = len(script_content.encode("utf-8"))
    if script_bytes > max_bytes:
        return f"Script exceeds the maximum size of {max_bytes} bytes"

    env_allows_unsafe = os.getenv("ASEPRITE_MCP_ALLOW_UNSAFE_LUA", "").strip().lower() in {"1", "true", "yes", "on"}
    if allow_unsafe_lua or env_allows_unsafe:
        return None

    if _UNSAFE_LUA_PATTERNS.search(script_content):
        return (
            "Unsafe Lua patterns detected (dofile/loadfile/os./io./package./require). "
            "Set allow_unsafe_lua=True only for trusted scripts."
        )

    return None


class AsepriteCommand:
    """Helper class for running Aseprite commands."""
    
    @staticmethod
    def run_command(args, *, timeout=None, max_output_bytes=None):
        """Run an Aseprite command with proper error handling.
        
        Args:
            args: List of command arguments
            timeout: Optional process timeout in seconds
            max_output_bytes: Optional combined cap for captured stdout and stderr
            
        Returns:
            tuple: (success, output) where success is a boolean and output is the command output
        """
        cmd = [os.getenv('ASEPRITE_PATH', 'aseprite')] + args
        if max_output_bytes is not None:
            return AsepriteCommand._run_bounded_command(cmd, timeout, max_output_bytes)

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
            return True, result.stdout
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except subprocess.CalledProcessError as e:
            return False, e.stderr

    @staticmethod
    def _run_bounded_command(cmd, timeout, max_output_bytes):
        """Drain subprocess pipes while retaining only a bounded amount of output."""
        if max_output_bytes <= 0:
            return False, "Maximum command output size must be greater than zero"

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as e:
            return False, str(e)

        captured = {"stdout": bytearray(), "stderr": bytearray(), "total": 0, "truncated": False}
        capture_lock = threading.Lock()

        def drain(stream, key):
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    return
                with capture_lock:
                    remaining = max_output_bytes - captured["total"]
                    if remaining > 0:
                        kept = chunk[:remaining]
                        captured[key].extend(kept)
                        captured["total"] += len(kept)
                    if len(chunk) > max(remaining, 0):
                        captured["truncated"] = True

        readers = [
            threading.Thread(target=drain, args=(proc.stdout, "stdout"), daemon=True),
            threading.Thread(target=drain, args=(proc.stderr, "stderr"), daemon=True),
        ]
        for reader in readers:
            reader.start()

        timed_out = False
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
        finally:
            for reader in readers:
                reader.join()
            proc.stdout.close()
            proc.stderr.close()

        output = captured["stdout"].decode("utf-8", errors="replace")
        error = captured["stderr"].decode("utf-8", errors="replace")
        if captured["truncated"]:
            marker = "\n[output truncated]"
            output = output[:max_output_bytes] + marker
            error = error[:max_output_bytes] + marker if error else ""
        if timed_out:
            detail = error or output
            suffix = f": {detail}" if detail else ""
            return False, f"Command timed out after {timeout} seconds{suffix}"
        returncode = proc.returncode
        if returncode:
            return False, error or output or f"Command failed with exit code {returncode}"
        return True, output
    
    @staticmethod
    def execute_lua_script(
        script_content,
        filename=None,
        allow_unsafe_lua: bool = False,
        max_script_bytes: int = _MAX_LUA_SCRIPT_BYTES,
    ):
        """Execute a Lua script in Aseprite.

        Args:
            script_content: Lua script code to execute
            filename: Optional filename to open before executing script
            allow_unsafe_lua: When False, reject obvious host-level Lua APIs
            max_script_bytes: Per-call cap, further limited by server configuration

        Returns:
            tuple: (success, output)
        """
        validation_error = validate_lua_script(
            script_content,
            allow_unsafe_lua=allow_unsafe_lua,
            max_bytes=max_script_bytes,
        )
        if validation_error:
            return False, validation_error

        # Create a temporary file for the script
        with tempfile.NamedTemporaryFile(suffix='.lua', delete=False, mode='w') as tmp:
            tmp.write(script_content)
            script_path = tmp.name

        try:
            args = ["--batch"]
            if filename and os.path.exists(filename):
                args.append(filename)
            args.extend(["--script", script_path])

            success, output = AsepriteCommand.run_command(
                args,
                timeout=_LUA_TIMEOUT_SECONDS,
                max_output_bytes=_MAX_COMMAND_OUTPUT_BYTES,
            )
            return success, output
        finally:
            # Clean up the temporary script file
            os.remove(script_path)

    @staticmethod
    def execute_lua_script_checked(script_content, filename=None):
        """Execute a Lua script and surface in-script errors.

        Scripts using this helper signal failure by printing a line
        starting with "ERROR:" (batch-mode scripts cannot affect the
        process exit code from Lua).

        Returns:
            tuple: (success, output) where output is the error message
            when an ERROR: line was printed, or the raw stdout otherwise.
        """
        success, output = AsepriteCommand.execute_lua_script(script_content, filename)
        if not success:
            return False, output
        for line in output.splitlines():
            if line.startswith("ERROR:"):
                return False, line[len("ERROR:"):]
        return True, output

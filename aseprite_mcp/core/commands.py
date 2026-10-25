import os
import re
import subprocess
import tempfile

import dotenv

_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
dotenv.load_dotenv(dotenv_path=_ENV_PATH)

_MAX_LUA_SCRIPT_BYTES = int(os.getenv("ASEPRITE_MCP_MAX_LUA_BYTES", "65536"))
_UNSAFE_LUA_PATTERNS = re.compile(
    r"(?is)(?:\b(?:dofile|loadfile|load|loadstring|require|package\.|os\.|io\.|debug\.|jit\.)\b|" 
    r"(?:os\.(?:execute|remove|rename|setlocale|exit|tmpname|date|time)|"
    r"(?:io\.(?:open|popen|output|input|tmpfile))|"
    r"(?:package\.loadlib)|(?:_G\.(?:dofile|loadfile|load|require)))"
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
    """Reject obviously unsafe Lua before launching Aseprite.

    Unsafe execution is disabled by default to keep the MCP server within the
    least-privilege model. Set allow_unsafe_lua=True or the
    ASEPRITE_MCP_ALLOW_UNSAFE_LUA=1 environment variable only for trusted, case-by-case
    scripts that require host-level Lua features.
    """
    if not script_content or not script_content.strip():
        return "Script cannot be empty"

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
    def run_command(args):
        """Run an Aseprite command with proper error handling.
        
        Args:
            args: List of command arguments
            
        Returns:
            tuple: (success, output) where success is a boolean and output is the command output
        """
        try:
            cmd = [os.getenv('ASEPRITE_PATH', 'aseprite')] + args
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    @staticmethod
    def execute_lua_script(script_content, filename=None, allow_unsafe_lua: bool = False):
        """Execute a Lua script in Aseprite.

        Args:
            script_content: Lua script code to execute
            filename: Optional filename to open before executing script
            allow_unsafe_lua: When False, reject obvious host-level Lua APIs

        Returns:
            tuple: (success, output)
        """
        validation_error = validate_lua_script(script_content, allow_unsafe_lua=allow_unsafe_lua)
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

            success, output = AsepriteCommand.run_command(args)
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

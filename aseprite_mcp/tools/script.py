import os

from .. import mcp
from ..core.commands import AsepriteCommand, reject_traversal


@mcp.tool()
async def run_lua_script(
    script: str,
    filename: str = "",
    allow_unsafe_lua: bool = False,
    max_script_bytes: int = 65536,
) -> str:
    """Execute a bounded native Aseprite batch through MCP.

    Prefer dedicated tools for a small edit or inspection, and native range
    tools when they cover the task. Use this tool for related multi-cel,
    frame-timing and tag operations that lack a dedicated batch tool, instead
    of starting Aseprite separately for every small change. Validate the full
    plan and target frames/layers first; use app.activeSprite and
    app.transaction, save once, and print a compact result. Serialize writes
    to each sprite and split large batches at meaningful visual checkpoints.
    Keep pixel authoring in Aseprite through MCP. Keep allow_unsafe_lua=False;
    routine batching needs no host APIs or validation bypass. The full API is documented at
    https://www.aseprite.org/api/.

    A best-effort text check blocks common host-level Lua APIs such as
    os./io./dofile/require. It is not a sandbox and can be bypassed; Lua runs
    with the host user's privileges. Use OS-level isolation for untrusted
    scripts. Set allow_unsafe_lua=True only for trusted scripts that need those
    APIs. Execution is also time-limited and output is capped.

    Args:
        script: Lua source code to execute
        filename: Optional Aseprite file to open before running
        allow_unsafe_lua: Skip the best-effort host-API check for trusted scripts
        max_script_bytes: Hard cap on script size in bytes
    """
    if not script.strip():
        return "Script cannot be empty"
    if len(script.encode("utf-8")) > max_script_bytes:
        return f"Script exceeds the maximum size of {max_script_bytes} bytes"

    if filename:
        traversal_error = reject_traversal(filename)
        if traversal_error:
            return traversal_error
        if not os.path.exists(filename):
            return f"File {filename} not found"

    success, output = AsepriteCommand.execute_lua_script(
        script,
        filename or None,
        allow_unsafe_lua=allow_unsafe_lua,
    )
    if success:
        return output if output.strip() else "Script executed (no output printed)"
    return f"Script failed: {output}"

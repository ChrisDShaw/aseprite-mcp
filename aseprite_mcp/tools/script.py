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
    """Execute Aseprite Lua code in batch mode (last resort).

    Reach for a dedicated tool first: draw_rows / read_rows to place and
    read pixels as text, draw_text for numbers and labels, replace_color or
    remap_colors_in_cel_range to recolour, export_animation or export_tag
    for GIFs, compare_frames and get_bounds to measure motion, view_sprite
    to look. Use Lua only for what none of them covers, such as a custom
    procedural effect. The full API is documented at
    https://www.aseprite.org/api/.

    By default, unsafe host-level Lua APIs such as os./io./dofile/require are
    blocked. Set allow_unsafe_lua=True only for a trusted script that explicitly
    requires host access. In production, prefer leaving this disabled and using
    the dedicated editing tools instead.

    Args:
        script: Lua source code to execute
        filename: Optional Aseprite file to open before running
        allow_unsafe_lua: Allow host-level Lua features for trusted scripts
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

"""Aseprite MCP - Model Context Protocol implementation for Aseprite."""

from functools import wraps
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError


_TOOL_ERROR_PREFIXES = (
    "Cannot ",
    "Directory ",
    "ERROR:",
    "Failed",
    "File ",
    "Invalid",
    "No preview server",
    "Port ",
    "Script cannot",
    "Script failed:",
    "Script exceeds",
    "Unsafe Lua",
    "Width and height",
    "scale must ",
)


class AsepriteMCP(FastMCP):
    """FastMCP server that marks established error-string responses as tool errors."""

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        register_tool = super().tool(*args, **kwargs)

        def decorator(func: Any) -> Any:
            @wraps(func)
            async def checked_tool(*call_args: Any, **call_kwargs: Any) -> Any:
                result = await func(*call_args, **call_kwargs)
                if isinstance(result, str) and result.startswith(_TOOL_ERROR_PREFIXES):
                    raise ToolError(result)
                return result

            register_tool(checked_tool)
            return func

        return decorator


INSTRUCTIONS = """\
Tools for drawing and animating pixel art in Aseprite. Sprites are small (16-64 px; a scene with a \
character needs 128 px or more): work in passes and check each one.

1. Plan: write down the pixel box of each part (head, torso, legs, weapon) first; leave a 1-2 px margin.
2. Silhouette in one flat color. Use shape tools (draw_line_at, draw_ellipse_at, fill_area_at) for big \
forms and draw_rows for details: rows of characters plus a colour legend, like ASCII art. Hands, faces, \
animals and handles under ~12 px are drawn pixel by pixel with draw_rows, never built from shapes. \
Clean edges: equal steps on straight diagonals (1-1-1, 2-2-2), gradual steps on curves (1,2,3 not 1,3,1), \
no L-shaped doubles on 1 px lines, no lone pixels.
3. Reuse an agreed palette. Otherwise build it once before coloring: generate_color_ramp (steps=3-4) \
per material, 8-16 colors in total. Neighbouring materials must differ in lightness, not just hue.
4. Flats, then shade from one light (top-left): highlight on the lit side, shadow on the far side and \
under overhangs (chin, arms). Pillow shading (light center, dark ring at the edge) is wrong. \
No dithering or anti-aliasing on sprites under 32 px.
5. Outline in one dark color (darkest ramp step or near-black), never lighter than the fill \
(selective outlines only on larger sprites). outline_cel adds 1 px outside the shape (region= for one object).
6. Review meaningful art passes with view_sprite (region="x,y,w,h" for details; up to 16 key frames \
per contact sheet). Use lint_sprite for changed geometry and get_color_stats for palette checks, \
then verify the finished package. Do not repeat metadata, palette or bounds reads after every \
cel/timing edit; repeat checks when a change or failure warrants them. If it does not read, change \
the shape, not the details.
7. Objects sit fully on their surfaces, away from edges, and parts stay attached: a handle touches its \
mug, leaves grow from their pot.

Batch related work by sprite and art pass. Each command starts a fresh batch-mode Aseprite process, \
so avoid one call per cel, duration or tag for a whole animation. Prefer dedicated range/bulk tools \
(propagate_cels, remap_colors_in_cel_range, set_frame_duration_all). Use a dedicated tool for a small \
edit or inspection. When no dedicated batch tool covers the combined operation, prefer one bounded \
run_lua_script batch through this MCP: use app.activeSprite, validate inputs and frame/layer targets, \
apply the planned cel edits/timings/tags in app.transaction, save once, and print a compact result. \
Keep allow_unsafe_lua=False; batching does not require host APIs or disabling validation. Keep pixel \
authoring inside Aseprite through MCP rather than external bitmap-generation scripts. Serialize writes \
to the same sprite; parallel calls would load/save competing copies. Split large batches at visual \
review checkpoints and preserve a recoverable source before a substantial edit.

Create all frames before finalizing tags; set complete timing lists and tags together. Reuse approved \
palettes and static cels. Prefer native range copies/recolours over repeated read_rows/redraw cycles \
for identical artwork. Export PNG/JSON and clip previews once the pass is ready, grouping exports with export_spritesheet/export_animation/export_tag \
where supported. A single package audit/metadata report can serve several checks; keep key-pose \
visual review and meaningful final verification. Use read_rows/draw_rows for precise pixels, \
draw_text for labels, and compare_frames/get_bounds for a specific motion question.

Animate pose to pose: redraw each key pose (anticipation, action, follow-through) on its own frame, \
with the whole body involved and the feet on one ground line unless airborne. copy_frame, \
erase_region the part that moves, then redraw it. Tween or offset cels only for rigid objects and \
secondary motion, never as the main motion. Soft bodies (slimes, jelly) squash and stretch 30-50% \
and change shape on every frame in the air. Call animation_workflow_guide before animating \
(use_case "idle" for idle and breathing loops).
"""

mcp = AsepriteMCP("aseprite", instructions=INSTRUCTIONS)

__version__ = "0.1.0"
__author__ = "Divyansh Singh"

from .. import mcp

@mcp.tool()
async def animation_workflow_guide(use_case: str = "character") -> str:
    """Return a concise English guide for animating pixel art well.

    Read it before animating. use_case: "character" (people, creatures,
    attacks, jumps, walks), "idle" (idle and breathing loops, including a
    fighter's ready stance between attacks), "environment" (scenes,
    backgrounds, effects) or anything else for general advice.
    """
    use_case = (use_case or "character").strip().lower()
    header = "Animation Workflow Guide"
    if use_case == "character":
        bullets = [
            "List the key poses before drawing. A jump is crouch -> stretch on takeoff -> airborne -> squash on landing; an attack is windup -> strike -> follow-through. An attack is 4-6 frames, a jump 5-7, a walk 6-8.",
            "Draw each key pose on its own frame. copy_frame from the previous pose, erase_region the parts that move, then redraw them; never draw the new limb over the old one.",
            "On a big move the whole body takes part: weight shifts, torso leans or turns, head follows the torso. On small moves keep at least a 1 px bob or lean. Feet stay on the same ground line unless the character is airborne.",
            "Reuse the pixel boxes from the still: the head stays the same height and width in every frame. Check with render_onion_skin (scale 6), get_bounds (rise and fall frames should mirror) and compare_frames (layer_name/region to isolate a part): 0% means it did not change; a change box covering the whole sprite on a small move means it drifted.",
            "Add anticipation before big moves (lean back before a strike, crouch before a jump).",
            "Squash on impact, stretch on fast motion, and keep the overall volume about the same. Soft bodies (slimes, jelly) deform much more, 30-50% of their size, and change shape on every frame in the air, not only on takeoff and landing.",
            "For very fast moves, use one smear frame instead of in-betweens: the weapon or limb colors stretched along the arc, 1 frame only, 50-80 ms.",
            "Vary timing with set_frame_duration: 80-120 ms for normal frames, 150-250 ms for the anticipation hold, 50-80 ms for the strike.",
            "get_color_stats on each frame must report the same unique_colors count and the same colors. If one drifts, set_palette with your ramps and run quantize_to_palette.",
            "Outlines: one dark color is safest under 32 px. On larger sprites, selective outlining uses a darker outline where the body is in shadow and a lighter one where it is lit, but the outline must always be darker than the fill it borders and than the background.",
            "Idle and walk loops must close: the last frame flows into frame 1. Use set_tag direction pingpong for breathing.",
            "Use tween_cel_positions, offset_cel_positions or oscillate_cel_positions only for rigid objects and secondary motion (bobbing, breathing, hair, capes), never as the main animation.",
            "Tag the range with set_tag, then inspect it with view_sprite (frames=\"1-8\"); an animated GIF cannot be inspected. Use export_animation (scale, background) or export_tag as GIF only for the final deliverable.",
            "Run audit_animation to catch missing cels and layer problems.",
            "Example, a 4-frame sword slash: 1) windup, body leans back with the sword behind the head, 180 ms; 2) strike, sword swept forward as a smear arc, 60 ms; 3) extension, arm and sword fully forward, torso turned, 100 ms; 4) recovery, sword low, weight settling, 120 ms.",
        ]
    elif use_case == "idle":
        bullets = [
            "An idle is a 2-6 frame breathing loop, never a pose held still: a fighter idles before and after every attack, and the attack starts from and returns to the idle pose.",
            "Stance: feet about shoulder width or narrower, knees almost straight. A wide stance with bent knees reads as dancing as soon as it bobs.",
            "Breath: torso, shoulders and head rise and fall 1 px together, on the same frame; the head moves with the shoulders. Only hair, cloth and capes lag one frame behind.",
            "When the hips drop 1 px, the knees soften forward by 1 px. The feet never move.",
            "Arms and a held weapon follow the shoulders by 1 px; the weapon tip may lag a frame, like cloth.",
            "Timing: 150-300 ms per frame. Close the loop: the last frame flows into frame 1 (set_tag direction pingpong suits a 2-3 frame breath).",
            "Check with compare_frames(layer_name=..., region=<feet>) that the feet do not change, and get_bounds that the top of the head moves 1 px at most.",
        ]
    elif use_case == "environment":
        bullets = [
            "Pick the palette first (apply_palette_preset or set_palette) so every layer shares it.",
            "Keep the background lower in contrast and saturation than the foreground, so characters read on top of it.",
            "Build the base scene once and copy it with copy_sprite for variants.",
            "Use propagate_cels for static layers (sky, mountains, ground).",
            "Animate only the moving layers (clouds, birds, water). Tweens and offsets suit these well.",
            "Loops must line up: the last frame should flow into the first. Check with render_onion_skin.",
            "Copy reusable assets across scenes with copy_layers_between_sprites.",
            "Tag loops and export GIFs to check pacing.",
            "Run audit_animation or animation_sanitize to validate layer coverage and overlaps.",
        ]
    else:
        bullets = [
            "Plan the key poses or states first, then draw each one on its own frame.",
            "Redraw what changes between key frames; move or tween cels only for rigid parts and secondary motion.",
            "Use layer-targeted tools (*_at) to avoid active-cel drift.",
            "Propagate static layers across the frame range.",
            "Vary frame durations: hold important frames longer.",
            "Use tags for loop ranges and export previews early.",
            "Run audit_animation or animation_sanitize to validate layer coverage and overlaps.",
        ]

    lines = [header, f"Use case: {use_case}"]
    lines.extend([f"- {b}" for b in bullets])
    return "\n".join(lines)

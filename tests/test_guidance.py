"""Server instructions and animation_workflow_guide point at the right tools."""
from conftest import run

import aseprite_mcp
from aseprite_mcp.tools import guide


def test_instructions_point_at_view_sprite_and_rows():
    text = aseprite_mcp.INSTRUCTIONS
    assert "view_sprite" in text and "export_frame at scale 8" not in text
    for tool in ("draw_rows", "read_rows", "draw_text", "export_animation", "get_bounds", "lint_sprite"):
        assert tool in text, tool


def test_guide_has_an_idle_use_case():
    idle = run(guide.animation_workflow_guide("idle"))
    assert "Use case: idle" in idle and "dancing" in idle and "head moves with the shoulders" in idle


def test_guide_soft_bodies_and_view_sprite():
    character = run(guide.animation_workflow_guide("character"))
    assert "30-50%" in character
    assert "view_sprite" in character and "export_spritesheet at scale 4-8" not in character

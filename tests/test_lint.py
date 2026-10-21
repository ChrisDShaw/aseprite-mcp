"""lint_sprite (analysis.py): detached pieces, lone and orphan pixels."""
import json

from conftest import ok, run

from aseprite_mcp.tools import analysis, canvas, drawing

LEGEND = {"M": "#8B5A2B", "H": "#F0E6D2"}


def test_lint_finds_detached_and_lone_pixels(sprite):
    ok(run(canvas.add_layer(sprite, "mug")))
    ok(run(drawing.draw_rectangle_at(sprite, "mug", 1, 2, 2, 5, 5, "#8B5A2B", True)))
    ok(run(drawing.draw_rows(sprite, "mug", 1, 9, 3, ["MM"], LEGEND)))  # handle off the mug
    ok(run(drawing.draw_rows(sprite, "mug", 1, 20, 20, ["M"], LEGEND)))
    lint = json.loads(ok(run(analysis.lint_sprite(sprite, 1, "mug"))))
    assert lint["pieces"] == 3 and lint["main_piece_pixels"] == 25
    assert lint["detached"] == [{"x": 9, "y": 3, "width": 2, "height": 1, "pixels": 2}]
    assert lint["lone_pixels"] == [{"x": 20, "y": 20}]


def test_lint_finds_orphan_pixels(sprite):
    ok(run(drawing.draw_rows(sprite, "mug", 1, 4, 4, ["H"], LEGEND)))
    lint = json.loads(ok(run(analysis.lint_sprite(sprite, 1, "mug"))))
    assert {"x": 4, "y": 4, "color": "#F0E6D2"} in lint["orphan_pixels"]


def test_lint_diagonals_connect(sprite):
    ok(run(canvas.add_layer(sprite, "diag")))
    ok(run(drawing.draw_rows(sprite, "diag", 1, 0, 0, ["M..", ".M.", "..M"], LEGEND)))
    lint = json.loads(ok(run(analysis.lint_sprite(sprite, 1, "diag"))))
    assert lint["pieces"] == 1 and lint["orphan_pixel_count"] == 0


def test_lint_composite_and_errors(sprite):
    lint = json.loads(ok(run(analysis.lint_sprite(sprite))))
    assert lint["layer"] is None and lint["opaque_pixels"] > 0
    assert "not found" in run(analysis.lint_sprite(sprite, 1, "missing"))
    assert "out of range" in run(analysis.lint_sprite(sprite, 9))

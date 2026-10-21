"""draw_iso_box (drawing.py): 2:1 isometric boxes with clean 2-1 edges."""
from conftest import ok, run

from aseprite_mcp.tools import canvas, drawing, pixel_read

TOP, LEFT, RIGHT = "#E8C170", "#B5833B", "#7A5427"


def as_rows(faces):
    top, left, right = faces
    every = top | left | right
    xs, ys = [p[0] for p in every], [p[1] for p in every]
    return ["".join("T" if (x, y) in top else "L" if (x, y) in left else "R" if (x, y) in right else "."
                    for x in range(min(xs), max(xs) + 1)) for y in range(min(ys), max(ys) + 1)]


def test_iso_box_geometry():
    assert as_rows(drawing._iso_box_faces(10, 0, 0, 1, 1, 2)) == [
        "..TT..",
        "TTTTTT",
        "LLTTRR",
        "LLLRRR",
        "..LR..",
    ]
    top, left, right = drawing._iso_box_faces(8, 2, 0, 3, 2, 3)
    assert not (top & left or top & right or left & right), "faces never overlap"


def test_iso_flat_tile_is_a_rhombus():
    top, left, right = drawing._iso_box_faces(0, 0, 0, 1, 1, 0)
    assert not left and not right
    assert as_rows((top, left, right)) == ["..TT..", "TTTTTT", "..TT.."]


def color_at(sprite, x, y):
    return run(pixel_read.get_pixel_color(sprite, x, y, "room", 1)).lower()


def test_draw_iso_box(sprite):
    ok(run(canvas.add_layer(sprite, "room")))
    result = ok(run(drawing.draw_iso_box(sprite, "room", 1, 16, 4, 0, 3, 2, 3, TOP, LEFT, RIGHT, "#1A1C2C")))
    assert "covers x 12-23, y 1-9" in result
    # the top vertex sits h px above the back corner
    assert color_at(sprite, 16, 1).startswith(TOP.lower())
    assert color_at(sprite, 12, 4).startswith(LEFT.lower())
    assert color_at(sprite, 23, 5).startswith(RIGHT.lower())
    assert color_at(sprite, 16, 0).startswith("#1a1c2c"), "outline above the top vertex"


def test_draw_iso_box_rejects_bad_input(sprite):
    assert ">= 1" in run(drawing.draw_iso_box(sprite, "room", 1, 0, 0, 0, 0, 1, 1, TOP, LEFT, RIGHT))
    assert "Invalid color value for left" in run(
        drawing.draw_iso_box(sprite, "room", 1, 0, 0, 0, 1, 1, 1, TOP, "#nope", RIGHT))

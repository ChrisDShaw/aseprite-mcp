"""Measuring motion: compare_frames layer/region filters and get_bounds (analysis.py)."""
import json

from conftest import ok, run

from aseprite_mcp.tools import analysis, animation, canvas, drawing, fx, pixel_read


def test_compare_frames_by_layer_and_region(sprite):
    ok(run(animation.add_frames(sprite, 1, 100)))
    ok(run(canvas.add_layer(sprite, "fx")))
    ok(run(drawing.draw_rows(sprite, "fx", 2, 0, 0, ["X"], {"X": "#FFFFFF"})))
    assert json.loads(ok(run(analysis.compare_frames(sprite, 1, 2))))["changed_pixels"] == 1
    body = json.loads(ok(run(analysis.compare_frames(sprite, 1, 2, layer_name="body"))))
    assert body["changed_pixels"] == 0 and body["layer"] == "body"
    part = json.loads(ok(run(analysis.compare_frames(sprite, 1, 2, region="0,0,4,4"))))
    assert part["changed_pixels"] == 1 and part["total_pixels"] == 16
    assert part["changed_bounds"] == {"x": 0, "y": 0, "width": 1, "height": 1}


def test_compare_frames_rejects_bad_region(sprite):
    assert "outside" in run(analysis.compare_frames(sprite, 1, 2, region="40,40,4,4"))
    assert "Invalid region" in run(analysis.compare_frames(sprite, 1, 2, region="nope"))
    assert "not found" in run(analysis.compare_frames(sprite, 1, 2, layer_name="missing"))


def test_get_bounds_per_frame(sprite):
    bounds = json.loads(ok(run(analysis.get_bounds(sprite, "body"))))
    assert bounds["frames"] == [
        {"frame": 1, "x": 8, "y": 8, "width": 16, "height": 16},
        {"frame": 2, "x": 8, "y": 8, "width": 16, "height": 16},
    ]
    fx_bounds = json.loads(ok(run(analysis.get_bounds(sprite, "fx", "1-2"))))
    assert fx_bounds["frames"] == [{"frame": 1, "empty": True},
                                   {"frame": 2, "x": 0, "y": 0, "width": 1, "height": 1}]


def test_get_bounds_isolates_a_hidden_layer(sprite):
    ok(run(animation.set_layer_visibility(sprite, "fx", False)))
    hidden = json.loads(ok(run(analysis.get_bounds(sprite, "fx", "2"))))
    assert hidden["frames"] == [{"frame": 2, "x": 0, "y": 0, "width": 1, "height": 1}]
    visible = json.loads(ok(run(analysis.get_bounds(sprite, frames="2"))))
    assert visible["frames"] == [{"frame": 2, "x": 8, "y": 8, "width": 16, "height": 16}]


def test_get_bounds_rejects_bad_frames(sprite):
    assert "out of range" in run(analysis.get_bounds(sprite, frames="5"))
    assert "Invalid" in run(analysis.get_bounds(sprite, frames="a"))
    assert "Invalid range" in run(analysis.get_bounds(sprite, frames="3-1"))


def test_outline_cel_region_outlines_one_object(sprite):
    ok(run(canvas.add_layer(sprite, "parts")))
    ok(run(drawing.draw_rectangle_at(sprite, "parts", 1, 2, 2, 3, 3, "#3366FF", True)))
    ok(run(drawing.draw_rectangle_at(sprite, "parts", 1, 26, 26, 3, 3, "#3366FF", True)))
    ok(run(fx.outline_cel(sprite, "parts", 1, "#000000", False, "0,0,8,8")))
    assert run(pixel_read.get_pixel_color(sprite, 1, 2, "parts", 1)).lower().startswith("#000000")
    assert "a=0" in run(pixel_read.get_pixel_color(sprite, 25, 26, "parts", 1))
    assert "Invalid region" in run(fx.outline_cel(sprite, "parts", 1, "#000000", False, "1,2"))

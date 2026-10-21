"""export_animation (export.py): GIF / PNG sequence, scaled, on a background."""
import glob
import json

from PIL import Image as PILImage

from conftest import BASE, ok, run

from aseprite_mcp.tools import animation, export, pixel_read


def test_export_animation_on_a_background(sprite):
    ok(run(animation.add_frames(sprite, 2, 100)))
    ok(run(animation.set_tag(sprite, "clip", 1, 2, "forward")))
    out = f"{BASE}/anim_bg.gif"
    result = ok(run(export.export_animation(sprite, out, "clip", 2, "#E9EEF2")))
    assert "Tag 'clip'" in result
    with PILImage.open(out) as im:
        assert im.size == (64, 64)
        assert im.n_frames == 2, "only the tagged frames"
        assert im.convert("RGB").getpixel((0, 0)) == (0xE9, 0xEE, 0xF2)


def test_export_animation_leaves_the_sprite_alone(sprite):
    info = json.loads(ok(run(animation.get_sprite_info(sprite))))
    assert "export background" not in json.dumps(info)
    assert "a=0" in run(pixel_read.get_pixel_color(sprite, 0, 0, "body", 1))


def test_export_animation_keeps_transparency(sprite):
    out = f"{BASE}/anim.gif"
    ok(run(export.export_animation(sprite, out)))
    with PILImage.open(out) as im:
        assert im.n_frames == 3
        assert im.convert("RGBA").getpixel((0, 0))[3] == 0


def test_export_animation_png_sequence(sprite):
    ok(run(export.export_animation(sprite, f"{BASE}/seq/frame.png", scale=1)))
    assert len(glob.glob(f"{BASE}/seq/frame*.png")) == 3


def test_export_animation_rejects_bad_input(sprite):
    assert "Tag not found" in run(export.export_animation(sprite, f"{BASE}/x.gif", "nope"))
    assert "must end in" in run(export.export_animation(sprite, f"{BASE}/x.mp4"))
    assert run(export.export_animation(sprite, f"{BASE}/x.gif", background="#zz")).startswith("Invalid")
    assert "scale" in run(export.export_animation(sprite, f"{BASE}/x.gif", scale=0))

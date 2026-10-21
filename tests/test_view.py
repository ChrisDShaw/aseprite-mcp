"""view_sprite (view.py)."""
import io

from PIL import Image as PILImage

from conftest import BASE, ok, run

from aseprite_mcp.tools import animation, canvas, drawing, view


def image_of(result):
    text, img = result
    return text, PILImage.open(io.BytesIO(img.data))


def test_view_returns_an_image(sprite):
    text, im = image_of(ok(run(view.view_sprite(sprite, grid=False, rulers=False, scale=2))))
    assert "32x32" in text
    # one 64x64 frame inside the gap margin, plus the title strip
    assert im.size == (64 + 2 * view.GAP, 64 + view.TITLE_H + 2 * view.GAP)
    x, y = view.GAP + 16 * 2, view.GAP + view.TITLE_H + 16 * 2
    assert im.getpixel((x, y)) == (0xD0, 0x46, 0x48), "painted body must show at its sprite coordinates"


def test_view_lays_out_selected_frames(sprite):
    ok(run(animation.add_frames(sprite, 3, 100)))
    _, one = image_of(ok(run(view.view_sprite(sprite, frames="2", scale=4))))
    _, three = image_of(ok(run(view.view_sprite(sprite, frames="1,3-4", scale=4))))
    assert three.width > 2 * one.width and three.height == one.height


def test_view_auto_scale_fits_the_client(sprite):
    _, im = image_of(ok(run(view.view_sprite(sprite))))
    assert max(im.size) <= view.MAX_SHEET_PX


def test_view_saves_png(sprite):
    out = f"{BASE}/view.png"
    text, _ = ok(run(view.view_sprite(sprite, frames="1", output_filename=out)))
    assert out in text
    with PILImage.open(out) as im:
        assert im.format == "PNG"


def test_view_rejects_bad_input(sprite):
    assert "out of range" in run(view.view_sprite(sprite, frames="99"))
    assert "Invalid frames" in run(view.view_sprite(sprite, frames="a-b"))
    assert "not found" in run(view.view_sprite(sprite, layer_name="missing"))
    assert "not found" in run(view.view_sprite(f"{BASE}/nope.aseprite"))


def test_view_single_layer(sprite):
    text, _ = image_of(ok(run(view.view_sprite(sprite, frames="1", layer_name="body"))))
    assert "layer body" in text


def test_view_rejects_backwards_and_huge_ranges(sprite):
    assert "Invalid range" in run(view.view_sprite(sprite, frames="4-2"))
    assert "Invalid range" in run(view.view_sprite(sprite, frames="1,4-2"))
    assert "out of range" in run(view.view_sprite(sprite, frames="1-1000000000"))


def test_view_caps_an_explicit_scale(sprite):
    assert "larger than" in run(view.view_sprite(sprite, frames="1-4", scale=64))


def test_view_renders_frames_far_apart(sprite):
    text, im = image_of(ok(run(view.view_sprite(sprite, frames="1,4", scale=2, grid=False, rulers=False))))
    assert "frame(s) 1, 4" in text
    assert im.width == 2 * 64 + 3 * view.GAP


def test_view_layer_by_group_path(base_dir):
    path = f"{BASE}/view_group.aseprite"
    ok(run(canvas.create_canvas(16, 16, path)))
    ok(run(canvas.add_group(path, "char")))
    ok(run(canvas.add_layer(path, "arm", "char")))
    ok(run(drawing.draw_rectangle_at(path, "arm", 1, 2, 2, 4, 4, "#3366FF", True)))
    ok(run(view.view_sprite(path, layer_name="char/arm")))
    ok(run(view.view_sprite(path, layer_name="arm")))


def test_view_save_creates_folders(sprite):
    out = f"{BASE}/view/nested/v.png"
    text, _ = ok(run(view.view_sprite(sprite, frames="1", output_filename=out)))
    assert "Saved to" in text


def test_view_checker_matches_the_pattern():
    im = view._checker(5, 3)
    assert im.getpixel((0, 0)) == view.CHECKER[0] and im.getpixel((1, 0)) == view.CHECKER[1]
    assert im.getpixel((0, 1)) == view.CHECKER[1] and im.getpixel((4, 2)) == view.CHECKER[0]


def test_view_region_crops_in_sprite_coordinates(sprite):
    text, im = image_of(ok(run(view.view_sprite(sprite, frames="1", region="6,6,4,4", scale=4,
                                                grid=False, rulers=False))))
    assert "region 6,6 4x4" in text
    assert im.size == (16 + 2 * view.GAP, 16 + view.TITLE_H + 2 * view.GAP)
    top = view.GAP + view.TITLE_H
    # sprite (8,8) is the first red body pixel: region column 2, row 2
    assert im.getpixel((view.GAP + 2 * 4, top + 2 * 4)) == (0xD0, 0x46, 0x48)
    assert im.getpixel((view.GAP + 1 * 4, top + 1 * 4)) != (0xD0, 0x46, 0x48)


def test_view_region_auto_zooms_in(sprite):
    text, _ = image_of(ok(run(view.view_sprite(sprite, frames="1", region="8,8,12,12"))))
    assert "at 32x" in text  # 384 px / 12 px


def test_view_region_is_clipped_and_validated(sprite):
    text, _ = image_of(ok(run(view.view_sprite(sprite, frames="1", region="28,28,10,10", scale=4))))
    assert "region 28,28 4x4" in text
    assert "outside" in run(view.view_sprite(sprite, region="40,40,4,4"))
    assert "Invalid region" in run(view.view_sprite(sprite, region="1,2,3"))
    assert "Invalid region" in run(view.view_sprite(sprite, region="0,0,0,4"))


def test_view_lays_out_wide_frames_to_fit(base_dir):
    # 4 frames of an 80x58 sprite at 6x used to go 4 in a row (2120 px wide),
    # which the client shrank until 1 px moves could not be judged.
    path = f"{BASE}/view_wide.aseprite"
    ok(run(canvas.create_canvas(80, 58, path)))
    ok(run(animation.add_frames(path, 3, 100)))
    _, im = image_of(ok(run(view.view_sprite(path, frames="1-4", scale=6))))
    assert max(im.size) <= view.MAX_SHEET_PX
    text, im = image_of(ok(run(view.view_sprite(path, frames="1-4"))))
    assert "at 6x" in text and max(im.size) <= view.MAX_SHEET_PX

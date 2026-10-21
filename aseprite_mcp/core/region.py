"""Shared "x,y,w,h" region parsing for tools that work on part of a sprite."""


def parse_region(value: str) -> tuple[int, int, int, int] | str | None:
    """Parse "x,y,w,h" into a tuple.

    Returns None for an empty string (no region), the (x, y, w, h) tuple
    when valid, or an error message string.
    """
    if not value or not value.strip():
        return None
    parts = value.split(",")
    try:
        x, y, w, h = (int(p) for p in parts)
    except ValueError:
        return f"Invalid region '{value}': use \"x,y,w,h\" in sprite pixels, e.g. \"8,4,16,12\""
    if w <= 0 or h <= 0:
        return f"Invalid region '{value}': width and height must be > 0"
    return x, y, w, h

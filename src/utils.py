"""
General utility function not specific to any aspect of app tracking.
"""

from typing import Tuple

__all__ = ["sec2str", "int_to_rgb", "contrast", "fmt"]


def sec2str(sec: float) -> str:
    """Convert a number of seconds into a common string form."""

    sec = int(sec)
    h = sec // 3600
    m = sec // 60 % 60
    s = sec % 60

    if h:
        return "{:02}h{:02}m{:02}s".format(h, m, s)
    elif m:
        return "{:02}m{:02}s".format(m, s)
    else:
        return "{:02}s".format(s)


def int_to_rgb(col: int) -> Tuple[int, int, int]:
    b = col & 0xff
    g = col >> 8 & 0xff
    r = col >> 16 & 0xff
    return r, g, b


def contrast(col):
    """Return black or white hex color with that contrast the most with the input."""
    if isinstance(col, int):
        col = int_to_rgb(col)

    if sum(col) / 3 > 0x80:
        return 0x000000
    else:
        return 0xffffff


def fmt(s, fg=None, bg=None, reset=True):
    """
    Add ANSI escape codes to a string.

    [fg] and [bg] can either be an rgb tuple of integers
        or an index into COLORS.

    If [reset] is False, the colors and any ANSI flags are not cleared.
    """

    flags = ""

    if fg is not None:
        if isinstance(fg, int):
            r, g, b = int_to_rgb(fg)
        else:
            r, g, b = fg
        flags += f"38;2;{r};{g};{b};"

    if bg is not None:
        if isinstance(bg, int):
            r, g, b = int_to_rgb(bg)
        else:
            r, g, b = bg
        flags += f"48;2;{r};{g};{b};"

    flags = flags.strip(";")

    if reset:
        reset = "\033[m"
    else:
        reset = ""

    return "\033[" + flags + "m" + str(s) + reset

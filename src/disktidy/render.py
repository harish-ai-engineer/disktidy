"""Pretty terminal rendering: banner, boxed tables, bars, colored cells.

Alignment note: cells are padded as *plain* text (so widths are correct),
then an optional `cell_style` callback wraps the already-padded string in
ANSI codes. That keeps columns aligned even when colored.
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence

from . import __version__
from .util import Style, human_size

# cell_style(row_index, col_index, padded_text, raw_text) -> str
CellStyle = Callable[[int, int, str, str], str]


def banner(style: Style) -> str:
    title = style.bold(style.bright_magenta("disktidy"))
    ver = style.bright_blue(f"v{__version__}")
    tag = style.gray("analyze & safely reclaim disk space")
    spark = style.bright_magenta("*")
    return f"\n {spark} {title}  {ver}  {style.dim('-')}  {tag}"


def heading(style: Style, text: str) -> str:
    return "\n" + style.bold(style.bright_magenta(text))


def bar(style: Style, frac: float, width: int = 14) -> str:
    """A colored usage bar; `frac` is the *used* fraction (0..1)."""
    frac = min(max(frac, 0.0), 1.0)
    filled = int(round(frac * width))
    body = "█" * filled + "░" * (width - filled)
    color = style.bright_red if frac >= 0.9 else style.bright_yellow if frac >= 0.8 else style.bright_cyan
    return color(body)


def size_color(style: Style, nbytes: int, text: str) -> str:
    """Color a size string by magnitude: bright_red >=10G, bright_yellow >=1G, bright_green <1G."""
    if nbytes >= 10 * 1024**3:
        return style.bright_red(text)
    if nbytes >= 1024**3:
        return style.bright_yellow(text)
    return style.bright_green(text)


_SAFETY = {
    "safe": ("bright_green", "●"),
    "caution": ("bright_yellow", "▲"),
    "manual": ("bright_blue", "◆"),
}


def safety_badge(style: Style, kind: str, padded: str) -> str:
    color_name, _ = _SAFETY.get(kind, ("gray", "•"))
    return getattr(style, color_name)(padded)


def table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    style: Style,
    aligns: Optional[Sequence[str]] = None,
    cell_style: Optional[CellStyle] = None,
) -> str:
    cols = len(headers)
    aligns = list(aligns) if aligns else ["l"] * cols
    widths = [len(str(h)) for h in headers]
    srows = [[str(c) for c in r] for r in rows]
    for r in srows:
        for i in range(cols):
            widths[i] = max(widths[i], len(r[i]))

    bar_c = style.bright_blue("│")

    def rule(left: str, mid: str, right: str) -> str:
        return style.bright_blue(left + mid.join("─" * (w + 2) for w in widths) + right)

    def pad(text: str, i: int) -> str:
        return text.rjust(widths[i]) if aligns[i] == "r" else text.ljust(widths[i])

    lines = [rule("┌", "┬", "┐")]
    header_cells = [style.bold(style.bright_magenta(pad(str(h), i))) for i, h in enumerate(headers)]
    lines.append(f"{bar_c} " + f" {bar_c} ".join(header_cells) + f" {bar_c}")
    lines.append(rule("├", "┼", "┤"))

    for ri, r in enumerate(srows):
        cells = []
        for ci in range(cols):
            padded = pad(r[ci], ci)
            if cell_style:
                padded = cell_style(ri, ci, padded, r[ci])
            cells.append(padded)
        lines.append(f"{bar_c} " + f" {bar_c} ".join(cells) + f" {bar_c}")
    lines.append(rule("└", "┴", "┘"))
    return "\n".join(lines)


def kv_line(style: Style, label: str, value: str) -> str:
    return f"  {style.bright_blue(label)}  {value}"


__all__ = [
    "banner", "heading", "bar", "size_color", "safety_badge", "table",
    "kv_line", "human_size",
]

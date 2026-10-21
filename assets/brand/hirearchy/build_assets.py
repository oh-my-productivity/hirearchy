#!/usr/bin/env python3
"""Builds the Hirearchy brand SVGs in this directory from measured geometry (standard library only).

    python3 assets/brand/hirearchy/build_assets.py          # write the SVGs next to this file
    python3 assets/brand/hirearchy/build_assets.py --check  # exit 1 if a committed SVG differs from what is built

Source: "Hirearchy Logo System Board.png" (1536 x 1024). Everything is in that board's pixel units, so the board SVG lines up with the PNG.

* The mark (an "H" whose two legs end in dots, with a stem and a root dot on top) is constructed from the geometry measured on the board:
  one path for the H, three circles. See MARK below.
* The wordmark is the outline traced from the board's hero lockup (wordmark.path, absolute M/L/C, same units as the board).
* The captions of the board are outlined glyphs (labels.json, JetBrains Mono, SIL OFL 1.1), so no file needs a font.
* Every file is self-contained: no <text>, <image>, <use>, styles or fonts.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ----------------------------------------------------------------------------------------------------------------- palette
NAVY = "#051846"
ORANGE = "#fe5c3f"
WHITE = "#ffffff"
BOARD_BG = "#fafafa"
MONO_PANEL = "#f0f2f6"
DIVIDER = "#e1e5ea"
CAPTION = "#7b8cab"
CONNECTOR = "#4b5f8a"

# ----------------------------------------------------------------------------------------------------------------- the mark
# Units: 1 = one pixel of the board's hero lockup. Origin: x on the mark's axis of symmetry, y at the top of the root dot.
MARK = {
    "root_r": 21.0, "root_cy": 21.0,                      # the orange root dot
    "stem_half": 6.25, "stem_top": 46.76,                  # the stem between the root dot and the crossbar
    "cross_top": 86.79, "cross_bottom": 116.08,            # the crossbar of the H
    "leg_outer": 68.75,                                    # outer edge of a leg, from the axis
    "cap_r": 16.1, "cap_top": 52.56,                       # rounded top ("ear") of a leg
    "ear_inner": 36.55, "leg_inner": 39.75,                # inner edge of a leg at its top / below the crossbar (slight taper)
    "foot_r": 14.5, "leg_bottom": 157.91,                  # rounded foot of a leg
    "dot_x": 55.3, "dot_y": 178.68, "dot_r": 17.5,         # the two leaf dots under the legs
}
MARK_HEIGHT = MARK["dot_y"] + MARK["dot_r"]                # 196.18
MARK_HALF_WIDTH = MARK["dot_x"] + MARK["dot_r"]            # 72.8


def num(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def mark_path(ox: float, oy: float, s: float) -> str:
    m = MARK
    cap_cy = m["cap_top"] + m["cap_r"]
    foot_cy = m["leg_bottom"] - m["foot_r"]
    taper = (m["leg_inner"] - m["ear_inner"]) * (m["cross_top"] - cap_cy) / (m["cross_bottom"] - cap_cy)
    inner_at_cross = m["ear_inner"] + taper

    def P(x: float, y: float) -> str:
        return f"{num(ox + s * x)} {num(oy + s * y)}"

    def arc(r: float, x: float, y: float) -> str:
        return f"A{num(s * r)} {num(s * r)} 0 0 1 {P(x, y)}"

    o, e, l, c, st = m["leg_outer"], m["ear_inner"], m["leg_inner"], m["cap_r"], m["stem_half"]
    return (
        f"M{P(-o, cap_cy)}{arc(c, -e, cap_cy)}"
        f"L{P(-inner_at_cross, m['cross_top'])}L{P(-st, m['cross_top'])}L{P(-st, m['stem_top'])}L{P(st, m['stem_top'])}"
        f"L{P(st, m['cross_top'])}L{P(inner_at_cross, m['cross_top'])}L{P(e, cap_cy)}{arc(c, o, cap_cy)}"
        f"L{P(o, foot_cy)}{arc(m['foot_r'], l, foot_cy)}L{P(l, m['cross_bottom'])}L{P(-l, m['cross_bottom'])}"
        f"L{P(-l, foot_cy)}{arc(m['foot_r'], -o, foot_cy)}Z"
    )


def circle(cx: float, cy: float, r: float, fill: str) -> str:
    return f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" fill="{fill}"/>'


def mark_elements(
    ox: float, oy: float, s: float, body: str, leaf: str, root: str, root_boost: float = 1.0, root_at: tuple[float, float, float] | None = None
) -> list[str]:
    """The mark at scale s with its axis at x=ox and the top of the root dot at y=oy.

    root_boost enlarges the root dot (small sizes); root_at = (cx, cy, r) places it explicitly instead (used where the board's own
    drawing has the root dot a little off the canonical spot)."""
    m = MARK
    cx, cy, r = root_at if root_at else (ox, oy + s * m["root_cy"], s * m["root_r"] * root_boost)
    return [
        f'<path d="{mark_path(ox, oy, s)}" fill="{body}"/>',
        circle(cx, cy, r, root),
        circle(ox - s * m["dot_x"], oy + s * m["dot_y"], s * m["dot_r"], leaf),
        circle(ox + s * m["dot_x"], oy + s * m["dot_y"], s * m["dot_r"], leaf),
    ]


# ----------------------------------------------------------------------------------------------------------------- wordmark
# The hero lockup of the board: the mark has scale 1 with its axis at x=204.6 and its root dot top at y=105.04; the wordmark outline is
# stored in the same board coordinates. HERO_BOX is the lockup's bounding box there.
HERO_AXIS, HERO_TOP = 204.6, 105.04
HERO_BOX = (132.07, 105.04, 875.83, 301.35)
PAD = 24.0


def transform_outline(d: str, s: float, tx: float, ty: float, x0: float = 0.0, y0: float = 0.0) -> str:
    """Maps an absolute M/L/C/Z outline: p -> t + s * (p - p0)."""
    tokens = re.findall(r"[MLCZ]|-?\d+(?:\.\d+)?", d)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "Z":
            out.append("Z")
            i += 1
            continue
        count = 3 if t == "C" else 1
        out.append(t)
        i += 1
        pairs = []
        for _ in range(count):
            x, y = float(tokens[i]), float(tokens[i + 1])
            pairs.append(f"{num(tx + s * (x - x0))} {num(ty + s * (y - y0))}")
            i += 2
        out.append(" ".join(pairs))
    return "".join(out)


def read_wordmark() -> str:
    return (HERE / "wordmark.path").read_text(encoding="utf-8").strip()


def lockup_elements(x: float, y: float, s: float, word: str, mark_body: str, mark_leaf: str, mark_root: str) -> list[str]:
    """The lockup with the top-left corner of its bounding box at (x, y) and scale s (1 = the hero lockup of the board)."""
    bx, by = HERO_BOX[0], HERO_BOX[1]
    ox = x + (HERO_AXIS - bx) * s
    parts = mark_elements(ox, y + (HERO_TOP - by) * s, s, mark_body, mark_leaf, mark_root)
    parts.append(f'<path d="{transform_outline(read_wordmark(), s, x, y, bx, by)}" fill="{word}"/>')
    return parts


# ----------------------------------------------------------------------------------------------------------------- favicon
FAV_BOARD_SIZE = 114.4        # the tile on the board
FAV_RADIUS = 15.2
FAV_MARK_SCALE = 0.405        # the mark fills the tile a little more than a plain scale-down would suggest
FAV_MARK_TOP = 18.32          # top of the mark below the top of the tile (board pixels)
FAV_ROOT_BOOST = 1.15         # the root dot is enlarged so it survives at 16 px


def favicon_elements(x: float, y: float, size: float) -> list[str]:
    k = size / FAV_BOARD_SIZE
    parts = [f'<rect x="{num(x)}" y="{num(y)}" width="{num(size)}" height="{num(size)}" rx="{num(FAV_RADIUS * k)}" fill="{NAVY}"/>']
    parts += mark_elements(x + size / 2, y + FAV_MARK_TOP * k, FAV_MARK_SCALE * k, WHITE, WHITE, ORANGE, root_boost=FAV_ROOT_BOOST)
    return parts


# ----------------------------------------------------------------------------------------------------------------- recursive hero
# The board's tree, by generation: mark scale, top of the mark (where its root dot would start), the root dot as drawn (centre y, radius)
# and the axis x of every node. Node n of a generation hangs from node n // 2 of the one above.
TREE = [
    {"s": 0.982, "top": 91.75, "root_cy": 112.93, "root_r": 20.73, "axes": [1222.75]},
    {"s": 0.678, "top": 288.75, "root_cy": 300.42, "root_r": 14.98, "axes": [1106.75, 1335.12]},
    {"s": 0.399, "top": 433.88, "root_cy": 441.53, "root_r": 8.81, "axes": [1039.88, 1162.75, 1283.0, 1398.88]},
    {"s": 0.230, "top": 518.25, "root_cy": 522.45, "root_r": 5.55, "axes": [1006.38, 1071.38, 1134.0, 1191.75, 1254.38, 1311.25, 1368.75, 1432.25]},
]
TREE_LINE = [(2.0, 1.0), (1.6, 0.42), (1.2, 0.16)]  # (stroke width, opacity) of the connector into generation 1, 2, 3


def tree_elements(dx: float, dy: float) -> list[str]:
    lines: list[str] = []
    marks: list[str] = []
    for g, level in enumerate(TREE):
        s = level["s"]
        for i, ax in enumerate(level["axes"]):
            marks += mark_elements(ax + dx, level["top"] + dy, s, NAVY, NAVY, ORANGE, root_at=(ax + dx, level["root_cy"] + dy, level["root_r"]))
            if g:
                up = TREE[g - 1]
                ps = up["s"]
                px = up["axes"][i // 2] + (-1 if i % 2 == 0 else 1) * ps * MARK["dot_x"]
                py = up["top"] + ps * MARK["dot_y"]
                width, opacity = TREE_LINE[g - 1]
                op = "" if opacity == 1 else f' stroke-opacity="{num(opacity)}"'
                lines.append(
                    f'<line x1="{num(px + dx)}" y1="{num(py + dy)}" x2="{num(ax + dx)}" y2="{num(level["root_cy"] + dy)}" '
                    f'stroke="{CONNECTOR}" stroke-width="{num(width)}" stroke-linecap="round"{op}/>'
                )
    return lines + marks


def tree_bounds() -> tuple[float, float, float, float]:
    xs, ys = [], []
    for level in TREE:
        s = level["s"]
        for ax in level["axes"]:
            xs += [ax - s * MARK_HALF_WIDTH, ax + s * MARK_HALF_WIDTH]
            ys += [min(level["top"], level["root_cy"] - level["root_r"]), level["top"] + s * MARK_HEIGHT]
    return min(xs), min(ys), max(xs), max(ys)


# ----------------------------------------------------------------------------------------------------------------- documents
def svg(width: float, height: float, label: str, body: list[str]) -> str:
    w, h = num(width), num(height)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{label}">\n'
        f"<title>{label}</title>\n" + "\n".join(body) + "\n</svg>\n"
    )


def lockup_document(label: str, word: str, body: str, leaf: str, root: str) -> str:
    bx0, by0, bx1, by1 = HERO_BOX
    w, h = bx1 - bx0 + 2 * PAD, by1 - by0 + 2 * PAD
    return svg(w, h, label, lockup_elements(PAD, PAD, 1.0, word, body, leaf, root))


def mark_document(label: str, body: str, leaf: str, root: str) -> str:
    w, h = 180.0, 230.0
    return svg(w, h, label, mark_elements(w / 2, (h - MARK_HEIGHT) / 2, 1.0, body, leaf, root))


def recursive_document() -> str:
    x0, y0, x1, y1 = tree_bounds()
    w, h = x1 - x0 + 2 * PAD, y1 - y0 + 2 * PAD
    return svg(w, h, "Hirearchy recursive mark: the logo grows by one generation at a time", tree_elements(PAD - x0, PAD - y0))


def board_document() -> str:
    labels = json.loads((HERE / "labels.json").read_text(encoding="utf-8"))
    b: list[str] = [f'<rect width="1536" height="1024" fill="{BOARD_BG}"/>']
    for x, y0, y1 in ((334, 400, 648), (634, 400, 648), (912, 58, 655)):
        b.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="{DIVIDER}" stroke-width="1"/>')
    b.append(f'<line x1="0" y1="733.2" x2="1536" y2="733.2" stroke="{DIVIDER}" stroke-width="1"/>')
    b.append(f'<rect x="1019.7" y="733.5" width="516.3" height="290.5" fill="{MONO_PANEL}"/>')
    b.append(f'<rect x="512" y="733.5" width="507.7" height="290.5" fill="{NAVY}"/>')
    # hero lockup
    b += lockup_elements(HERO_BOX[0], HERO_BOX[1], 1.0, NAVY, NAVY, NAVY, ORANGE)
    # primary mark, single colour mark
    b += mark_elements(187.25, 407.25, 0.73, NAVY, NAVY, ORANGE)
    b += mark_elements(482.88, 408.12, 0.72, NAVY, NAVY, NAVY)
    # favicon tile
    b += favicon_elements(713.65, 432.8, FAV_BOARD_SIZE)
    # recursive hero
    b += tree_elements(0.0, 0.0)
    # the three lockups on their backgrounds: (mark scale, axis x, top y), (wordmark scale, x, y of the outline's point (332, 140))
    for (ms, mx, my), (ws, wx, wy), word, leaf, root in (
        ((0.49, 120.0, 794.88), (0.484, 186.5, 817.0), NAVY, NAVY, ORANGE),
        ((0.495, 626.5, 794.25), (0.492, 694.0, 816.38), WHITE, WHITE, ORANGE),
        ((0.48, 1154.12, 796.12), (0.464, 1218.0, 818.5), NAVY, NAVY, NAVY),
    ):
        b += mark_elements(mx, my, ms, word, leaf, root)
        b.append(f'<path d="{transform_outline(read_wordmark(), ws, wx, wy, 332.0, 140.0)}" fill="{word}"/>')
    for id_, label in labels.items():
        fill = WHITE if label["colour"] == "white" else CAPTION
        b.append(f'<g id="{id_}" fill="{fill}"><path d="{label["d"]}"/></g>')
    return svg(1536, 1024, "Hirearchy logo system board", b)


def build_all() -> dict[str, str]:
    return {
        "logo.svg": lockup_document("Hirearchy logo", NAVY, NAVY, NAVY, ORANGE),
        "logo-dark.svg": lockup_document("Hirearchy logo for dark backgrounds", WHITE, WHITE, WHITE, ORANGE),
        "logo-mono.svg": lockup_document("Hirearchy logo, single colour", NAVY, NAVY, NAVY, NAVY),
        "mark.svg": mark_document("Hirearchy mark", NAVY, NAVY, ORANGE),
        "mark-mono.svg": mark_document("Hirearchy mark, single colour", NAVY, NAVY, NAVY),
        "favicon.svg": svg(64, 64, "Hirearchy favicon", favicon_elements(0, 0, 64)),
        "mark-recursive.svg": recursive_document(),
        "brand-board.svg": board_document(),
    }


def main(argv: list[str]) -> int:
    built = build_all()
    if "--check" in argv:
        stale = [n for n, c in built.items() if not (HERE / n).is_file() or (HERE / n).read_text(encoding="utf-8") != c]
        for n in stale:
            print(f"stale: {n}", file=sys.stderr)
        return 1 if stale else 0
    for name, content in built.items():
        (HERE / name).write_text(content, encoding="utf-8")
        print(f"wrote {name} ({len(content):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

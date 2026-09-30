"""Draw the stats cards on their pixel-art backgrounds.
Every mark sits on the 5 px half grid (canvas 320 x 128) and uses the scene palette, so the cards match the README scenes."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).parent / "assets"
W, H, K = 1600, 640, 5
GOLD, EDGE = (245, 222, 160), (28, 18, 10)          # the scene-title pair
BOARD, WOOD = (0x3E, 0x2D, 0x21), (0x7C, 0x4B, 0x25)  # palette: dark wood fill, wood border
LIGHT, XP = (0xF2, 0xF0, 0xA0), (0xC8, 0x9B, 0x3C)
BAR, BAR_EMPTY = (0x76, 0xB8, 0x41), (0x0D, 0x3F, 0x2B)
TILE_COLORS = {".": (0x1D, 0x4A, 0x32), ",": (0x2F, 0x53, 0x2F), "s": (0x76, 0xB8, 0x41), "b": (0x4A, 0x91, 0x3C),
               "l": (0x36, 0x80, 0x4A), "L": (0x76, 0xB8, 0x41), "t": (0x7C, 0x4B, 0x25)}
TILES = [  # 5x5 sprites by GitHub contribution level: grass, sprout, bush, small tree, big tree
    [".....", ".,...", ".....", "...,.", "....."],
    [".....", ".....", ".s.s.", "..s..", ".,.,."],
    [".....", ".bbb.", "bbLbb", "bbbbb", ".,.,."],
    ["..l..", ".lLl.", ".lll.", "..t..", ".,t,."],
    [".lLl.", "lLlLl", "lllll", ".ltl.", "..t.."],
]
TITLE = ImageFont.truetype(str(ASSETS / "NodestoCapsCondensed-Bold.otf"), 30)
PIXEL = ImageFont.truetype(str(ASSETS / "PressStart2P-Regular.ttf"), 8)


def palette():
    return set(Image.open(ASSETS / "palette.png").convert("RGB").getdata())


def fit(d, s, font, max_w):
    """Trim to max_w half-px with '...' so long names and descriptions stay inside their panel."""
    if d.textlength(s, font=font) <= max_w:
        return s
    while s and d.textlength(s + "...", font=font) > max_w:
        s = s[:-1]
    return s.rstrip() + "..."


def ago(days):
    return "today" if days == 0 else f"{days}d ago"


class Card:
    """A background plus one transparent layer on the half grid; flatten() upscales the layer with hard edges."""

    def __init__(self, bg):
        self.bg = Image.open(ASSETS / bg).convert("RGB")
        self.layer = Image.new("RGBA", (W // K, H // K), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.layer)
        self.d.fontmode = "1"  # no antialiasing: only exact palette colors

    def title(self, text, x, y):
        l, t, _, _ = self.d.textbbox((0, 0), text, font=TITLE)
        x, y = x - l + 1, y - t + 1  # +1 leaves room for the outline
        # Pillow antialiases strokes even in fontmode "1", so the 1 px outline and the drop shadow are stamped as offsets.
        for dx in (-1, 0, 1, 2):
            for dy in (-1, 0, 1, 2):
                self.d.text((x + dx, y + dy), text, font=TITLE, fill=EDGE)
        self.d.text((x, y), text, font=TITLE, fill=GOLD)

    def panel(self, x, y, w, h):
        """Wooden board with cut corners, snapped to whole 10 px art pixels."""
        x, y, w, h = (v // 2 * 2 for v in (x, y, w, h))
        self.d.rectangle((x + 2, y, x + w - 3, y + h - 1), fill=EDGE)
        self.d.rectangle((x, y + 2, x + w - 1, y + h - 3), fill=EDGE)
        self.d.rectangle((x + 1, y + 1, x + w - 2, y + h - 2), fill=WOOD)
        self.d.rectangle((x + 3, y + 3, x + w - 4, y + h - 4), fill=BOARD)

    def text(self, s, x, y, fill=GOLD, max_w=None):
        self.d.text((x, y), fit(self.d, s, PIXEL, max_w) if max_w else s, font=PIXEL, fill=fill)

    def row(self, label, value, x, y, w):
        self.text(label, x, y)
        self.text(value, x + w - int(self.d.textlength(value, font=PIXEL)), y, LIGHT)

    def bar(self, x, y, w, frac, fill=BAR):
        self.d.rectangle((x, y, x + w - 1, y + 3), fill=EDGE)
        self.d.rectangle((x + 1, y + 1, x + w - 2, y + 2), fill=BAR_EMPTY)
        n = round((w - 2) * max(0.0, min(1.0, frac)) / 2) * 2  # whole art pixels
        if n:
            self.d.rectangle((x + 1, y + 1, x + n, y + 2), fill=fill)

    def tile(self, x, y, lvl):
        for j, line in enumerate(TILES[lvl]):
            for i, ch in enumerate(line):
                self.d.point((x + i, y + j), fill=TILE_COLORS[ch])

    def flatten(self):
        out = self.bg.convert("RGBA")
        out.alpha_composite(self.layer.resize((W, H), Image.Resampling.NEAREST))
        return out.convert("RGB")


def character(s):
    c = Card("bg-character.png")
    c.title("Character Sheet", 8, 4)
    c.panel(8, 32, 304, 90)
    x, y = 14, 38
    c.text(f"LEVEL {s['level']}", x, y)
    c.bar(x, y + 11, 136, s["xp"], XP)
    c.text("FULL STACK DEV", x, y + 19, LIGHT)
    for i, (k, v) in enumerate((("COMMITS", s["commits"]), ("PRS", s["prs"]), ("REPOS", s["repos"]), ("STARS", s["stars"]))):
        c.row(k, f"{v:,}", x, y + 30 + 11 * i, 136)
    c.text("PROFICIENCIES", 164, y)
    top = s["languages"][0][1] if s["languages"] else 1
    for i, (name, share) in enumerate(s["languages"]):
        c.text(name, 164, y + 11 + 11 * i, LIGHT, max_w=84)
        c.bar(252, y + 13 + 11 * i, 54, share / top)  # full bar = most used language
    return c.flatten()


def quests(s):
    c = Card("bg-quests.png")
    c.title("Recent Quests", 8, 4)
    for i, q in enumerate(s["quests"]):
        y = 32 + 32 * i
        c.panel(8, y, 304, 28)
        right = " ".join(p for p in (q["lang"], ago(q["days"])) if p)
        rw = int(c.d.textlength(right, font=PIXEL))
        c.text(right, 306 - rw, y + 6, LIGHT)
        c.text(q["name"], 14, y + 6, max_w=306 - rw - 8 - 14)
        c.text(q["desc"], 14, y + 16, LIGHT, max_w=292)
    return c.flatten()


def forest(s):
    c = Card("bg-forest.png")
    c.title("Contribution Forest", 8, 4)
    c.panel(20, 32, 280, 64)
    c.text(f"STREAK {s['current']:,}  BEST {s['longest']:,}  TOTAL {s['total']:,}", 26, 38, max_w=268)
    for col, row, lvl in s["days"]:
        c.tile(27 + 5 * col, 54 + 5 * row, lvl)
    return c.flatten()

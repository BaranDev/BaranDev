"""Draw the stats cards into their pixel-art backgrounds: ink on the book pages, notes pinned to the quest board, a grove
growing on the clearing's grass. Every mark sits on the 5 px half grid (canvas 320 x 128) and uses the scene palette, so the
cards match the README scenes. Layout coordinates are in half-grid units and follow the pages, board and grass of each background."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).parent / "assets"
W, H, K = 1600, 640, 5
GOLD, EDGE = (245, 222, 160), (28, 18, 10)            # the scene-title pair
INK, PAPER, SHADE = (0x24, 0x15, 0x16), (0xF2, 0xF0, 0xA0), (0xC8, 0x9B, 0x3C)  # palette: ink, parchment, parchment edge
PIN, BAR, XP = (0xAA, 0x52, 0x29), (0x36, 0x80, 0x4A), (0xC1, 0x75, 0x30)
TILE_COLORS = {"d": (0x1D, 0x4A, 0x32), "L": (0x4A, 0x91, 0x3C), "t": (0x54, 0x2B, 0x1C)}
TILES = [  # 4x4 plants by GitHub contribution level, dark enough to read on the bright grass; "." stays transparent
    None,                                  # no contributions: bare grass
    ["....", ".dd.", "dLdd", ".dd."],      # any contribution grows a bush
    [".dd.", "dLdd", ".dd.", ".t.."],
    ["dLdd", "dddL", "dLdd", ".tt."],
    ["dLLd", "dLdL", "dddd", ".tt."],
]
TITLE = ImageFont.truetype(str(ASSETS / "NodestoCapsCondensed-Bold.otf"), 30)
PIXEL = ImageFont.truetype(str(ASSETS / "Tiny5-Regular.ttf"), 8)


def palette():
    return set(Image.open(ASSETS / "palette.png").convert("RGB").getdata())


def fit(d, s, font, max_w):
    """Trim to max_w half-px with '...' so long names and descriptions stay inside their space."""
    if d.textlength(s, font=font) <= max_w:
        return s
    while s and d.textlength(s + "...", font=font) > max_w:
        s = s[:-1]
    return s.rstrip() + "..."


def wrap(d, s, font, max_w, max_lines):
    """Break a repo name into lines of max_w, preferring hyphens and underscores; the last line is trimmed with '...'."""
    lines = []
    while s and len(lines) < max_lines - 1 and d.textlength(s, font=font) > max_w:
        cut = len(s)
        while cut > 1 and d.textlength(s[:cut], font=font) > max_w:
            cut -= 1
        soft = max(s.rfind("-", 0, cut), s.rfind("_", 0, cut))
        cut = soft + 1 if soft > 0 else cut
        lines.append(s[:cut])
        s = s[cut:]
    return lines + [fit(d, s, font, max_w)] if s else lines


def ago(days):
    return "today" if days == 0 else f"{days}d ago"


class Card:
    """A background plus one transparent layer on the half grid; flatten() upscales the layer with hard edges."""

    def __init__(self, bg):
        self.bg = Image.open(ASSETS / bg).convert("RGB")
        self.layer = Image.new("RGBA", (W // K, H // K), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.layer)
        self.d.fontmode = "1"  # no antialiasing: only exact palette colors

    def outlined(self, text, x, y, font, shadow=True):
        """Gold text with a 1 px dark outline (and drop shadow), stamped as offsets: Pillow antialiases real strokes."""
        l, t, _, _ = self.d.textbbox((0, 0), text, font=font)
        x, y = x - l + 1, y - t + 1
        span = (-1, 0, 1, 2) if shadow else (-1, 0, 1)
        for dx in span:
            for dy in span:
                self.d.text((x + dx, y + dy), text, font=font, fill=EDGE)
        self.d.text((x, y), text, font=font, fill=GOLD)

    def title(self, text, x, y):
        self.outlined(text, x, y, TITLE)

    def text(self, s, x, y, fill=INK, max_w=None):
        self.d.text((x, y), fit(self.d, s, PIXEL, max_w) if max_w else s, font=PIXEL, fill=fill)

    def row(self, label, value, x, y, w):
        self.text(label, x, y)
        self.text(value, x + w - int(self.d.textlength(value, font=PIXEL)), y)

    def bar(self, x, y, w, frac, fill=BAR):
        """Thin bar on parchment: a 2 px track in the parchment's edge color, filled in whole art pixels."""
        self.d.rectangle((x, y, x + w - 1, y + 1), fill=SHADE)
        n = round(w * max(0.0, min(1.0, frac)) / 2) * 2
        if n:
            self.d.rectangle((x, y, x + n - 1, y + 1), fill=fill)

    def note(self, x, y, w, h):
        """A parchment note pinned to the board, like the ones painted in the background."""
        self.d.rectangle((x + 1, y + 1, x + w, y + h), fill=SHADE)  # edge shadow
        self.d.rectangle((x, y, x + w - 1, y + h - 1), fill=PAPER)
        self.d.rectangle((x + w // 2 - 1, y + 1, x + w // 2, y + 2), fill=PIN)

    def tile(self, x, y, lvl):
        for j, line in enumerate(TILES[lvl] or []):
            for i, ch in enumerate(line):
                if ch != ".":
                    self.d.point((x + i, y + j), fill=TILE_COLORS[ch])

    def flatten(self):
        out = self.bg.convert("RGBA")
        out.alpha_composite(self.layer.resize((W, H), Image.Resampling.NEAREST))
        return out.convert("RGB")


def character(s):
    c = Card("bg-character.png")
    c.title("Character", 8, 40)  # stacked on the foliage left of the book, clear of the pages
    c.title("Sheet", 8, 64)
    c.outlined("Full Stack Developer", 10, 92, PIXEL, shadow=False)
    left, right, top, page = 112, 172, 30, 48  # the book's two pages (parchment spans x 106-222, y 26-87)
    c.text(f"Level {s['level']}", left, top)
    c.bar(left, top + 8, page, s["xp"], XP)
    for i, (k, v) in enumerate((("Commits", s["commits"]), ("PRs", s["prs"]), ("Repos", s["repos"]), ("Stars", s["stars"]))):
        c.row(k, f"{v:,}", left, top + 14 + 10 * i, page)
    most = s["languages"][0][1] if s["languages"] else 1
    for i, (name, share) in enumerate(s["languages"]):
        c.text(name, right, top + 11 * i, max_w=page)
        c.bar(right, top + 7 + 11 * i, page, share / most)  # full bar = most used language
    return c.flatten()


def quests(s):
    c = Card("bg-quests.png")
    c.title("Recent Quests", 8, 4)
    for i, q in enumerate(s["quests"]):
        x = 94 + 47 * i  # three notes across the board
        c.note(x, 32, 43, 54)
        y = 37
        for line in wrap(c.d, q["name"], PIXEL, 39, 3):
            c.text(line, x + 2, y)
            y += 7
        c.text(q["lang"], x + 2, 70, max_w=39)
        c.text(ago(q["days"]), x + 2, 77, max_w=39)
    return c.flatten()


def forest(s):
    c = Card("bg-forest.png")
    c.title("Contribution Forest", 8, 4)
    stats = f"Streak {s['current']:,}   Best {s['longest']:,}   Total {s['total']:,}"
    c.outlined(stats, (W // K - int(c.d.textlength(stats, font=PIXEL))) // 2, 40, PIXEL, shadow=False)
    for col, row, lvl in s["days"]:
        c.tile(54 + 4 * col, 84 + 4 * row, lvl)  # 53 weeks x 7 days of plants on the grass
    return c.flatten()

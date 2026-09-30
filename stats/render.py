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
TREES = [None] + [Image.open(ASSETS / f"tree-{i}.png").convert("RGBA") for i in (1, 2, 3, 4)]  # sapling, young, great, greatest
FIREFLY = (0xCB, 0xD5, 0x51)
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
        """Label left, value right-aligned; the label gives way (trimmed with '...') so big numbers never collide."""
        vw = int(self.d.textlength(value, font=PIXEL))
        label = fit(self.d, label, PIXEL, w - vw - 2)
        self.text(label, x, y)
        self.text(value, x + w - vw, y)
        return label

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

    def sprite(self, im, cx, ground):
        """Stand an art-pixel sprite on the ground line, centered on cx (half-grid units); returns its top y."""
        big = im.resize((im.width * 2, im.height * 2), Image.Resampling.NEAREST)  # 1 art px = 2 half px
        x, y = cx - big.width // 2 // 2 * 2, ground - big.height
        self.layer.alpha_composite(big, (x, y))
        return y

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
    return [c.flatten()]


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
    return [c.flatten()]


def stages(months):
    """Growth stage per month: 0 none, 1 sapling, 2 young, 3 great, 4 the single greatest tree for the best month
    (a tie goes to the newest month)."""
    counts = [n for _, n in months]
    most = max(counts, default=0)
    if not most:
        return [0] * len(counts)
    best = len(counts) - 1 - counts[::-1].index(most)
    return [4 if i == best else 0 if n == 0 else 1 if n <= most * 0.15 else 2 if n <= most * 0.5 else 3  # quiet months stay saplings
            for i, n in enumerate(counts)]


BOB = (0, 0, -1, -1, -2, -2, -1, -1)  # half-px float offsets per frame: a slow up-and-down loop


def forest(s):
    """A grove of the last 12 months: each month is a tree whose growth stage follows its contributions, the count at its
    foot and the month's name floating above it. Returns the animation frames (the month names bob, each a step out of phase)."""
    c = Card("bg-forest.png")
    c.title("Contribution Forest", 8, 4)
    c.outlined(str(s["year"]), 10, 30, PIXEL, shadow=False)  # small subtitle, same style as the character card's class line
    stats = f"Streak {s['current']:,}   Best {s['longest']:,}   Total {s['total']:,}"
    c.outlined(stats, (W // K - int(c.d.textlength(stats, font=PIXEL))) // 2, 33, PIXEL, shadow=False)
    ground, labels = 112, []
    for i, ((label, n), stage) in enumerate(zip(s["months"], stages(s["months"]))):
        cx = 16 + 24 * i + 12  # 12 slots across the whole grass line
        top = c.sprite(TREES[stage], cx, ground) if stage else ground - 2
        num = f"{n:,}"
        c.outlined(num, cx - int(c.d.textlength(num, font=PIXEL)) // 2, ground + 3, PIXEL, shadow=False)
        labels.append((label, cx - int(c.d.textlength(label, font=PIXEL)) // 2, top - 10, i))
        if i == len(s["months"]) - 1:  # this month: fireflies around its tree
            for dx, dy in ((-10, -4), (9, -8), (-7, -14), (11, -2)):
                c.d.rectangle((cx + dx // 2 * 2, top + 10 + dy // 2 * 2, cx + dx // 2 * 2 + 1, top + 11 + dy // 2 * 2), fill=FIREFLY)
    base, frames = c.layer, []
    for f in range(len(BOB)):
        c.layer = base.copy()
        c.d = ImageDraw.Draw(c.layer)
        c.d.fontmode = "1"
        for label, x, y, i in labels:
            c.outlined(label, x, y + BOB[(f + i) % len(BOB)], PIXEL, shadow=False)
        frames.append(c.flatten())
    return frames

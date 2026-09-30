# stats/test_stats.py  -- run: python stats/test_stats.py
from datetime import date

import data
import render


def day(d, n, lvl="NONE"):
    return {"date": d, "contributionCount": n, "contributionLevel": lvl}


def repo(name, desc="d", lang="Python", pushed="2026-09-30T10:00:00Z", stars=1, langs=(("Python", 100),)):
    return {"name": name, "description": desc, "stargazerCount": stars, "pushedAt": pushed,
            "primaryLanguage": {"name": lang} if lang else None,
            "languages": {"edges": [{"size": s, "node": {"name": n}} for n, s in langs]}}


def test_data():
    hist = [day("2026-01-01", 1), day("2026-01-02", 2), day("2026-01-03", 0), day("2026-01-04", 1),
            day("2026-01-05", 3), day("2026-01-06", 0), day("2026-01-05", 3)]  # 01-05 repeated: boundary day from two yearly queries
    assert data.streaks(hist, date(2026, 1, 6)) == (2, 2)   # today empty so far: streak still counts from yesterday
    assert data.streaks(hist, date(2026, 1, 7)) == (0, 2)   # a full empty day breaks it
    assert data.level(0) == (1, 0.0)
    assert data.level(49) == (1, 0.98)
    assert data.level(50) == (2, 0.0)
    assert data.level(150) == (3, 0.0)
    assert data.age(date(2003, 5, 10), date(2026, 5, 10)) == (23, 0.0)       # birthday: level up, empty bar
    lvl, frac = data.age(date(2003, 5, 10), date(2026, 5, 9))
    assert lvl == 22 and 0.99 < frac < 1                                        # day before: bar almost full
    assert data.age(date(2004, 2, 29), date(2026, 2, 28))[0] == 21              # leap-day birthday in a common year
    assert data.age(date(2004, 2, 29), date(2026, 3, 1))[0] == 22
    langs = data.languages([repo("a", langs=(("Python", 300), ("HTML", 100))), repo("b", langs=(("Python", 100),))])
    assert langs == [("Python", 0.8), ("HTML", 0.2)]
    qs = data.quests([repo("BaranDev"), repo("x", desc=None, lang=None, pushed="2026-09-28T23:00:00Z"), repo("y"), repo("z"), repo("w")],
                     "barandev", date(2026, 10, 1))
    assert [q["name"] for q in qs] == ["x", "y", "z"]         # profile repo skipped, 3 max
    assert qs[0] == {"name": "x", "lang": "", "days": 3}
    user = {"login": "barandev", "pullRequests": {"totalCount": 7},
            "repositories": {"totalCount": 2, "nodes": [repo("a", stars=3), repo("b", stars=4)]},
            "contributionsCollection": {"totalCommitContributions": 5, "contributionCalendar": {"weeks": [
                {"contributionDays": [day("2026-01-04", 1, "FIRST_QUARTILE"), day("2026-01-05", 3, "FOURTH_QUARTILE")]}]}},
            "history": hist}
    s = data.derive(user, date(2026, 1, 6))
    assert data.derive(user, date(2026, 1, 6), birth=date(2003, 1, 6))["level"] == 23   # level = age when a birth date is set
    assert (s["total"], s["stars"], s["prs"], s["repos"], s["commits"]) == (7, 7, 7, 2, 5)  # 01-05 counted once
    assert len(s["months"]) == 12 and s["months"][0] == ("Feb", 0)            # the 12 months ending this month
    assert s["months"][-1] == ("Jan", 7)                                         # Jan 2026 total, 01-05 counted once


SAMPLE = {"login": "barandev", "level": 18, "xp": 0.42, "total": 12345, "commits": 85, "prs": 197, "repos": 25, "stars": 12,
          "languages": [("TypeScript", 0.5), ("Python", 0.2), ("JavaScript", 0.15), ("C#", 0.1), ("HTML", 0.05)],
          "quests": [{"name": "a-very-long-repository-name-that-cannot-possibly-fit", "lang": "TypeScript", "days": 0},
                     {"name": "winhub", "lang": "", "days": 36}],
          "months": [(m, n) for m, n in zip("Nov Dec Jan Feb Mar Apr May Jun Jul Aug Sep Oct".split(), (0, 5, 40, 120, 9, 0, 300, 77, 1, 64, 210, 12))],
          "current": 12, "longest": 40}


def test_render():
    allowed = render.palette() | {render.GOLD, render.EDGE}
    for s in (SAMPLE, dict(SAMPLE, languages=[], quests=[])):   # also an account with no languages or repos
        for fn in (render.character, render.quests, render.forest):
            for im in fn(s):                                        # every card is a list of frames
                assert im.size == (1600, 640), fn.__name__
                stray = {c for _, c in im.getcolors(1 << 16)} - allowed
                assert not stray, (fn.__name__, list(stray)[:5])  # identical style: palette + title colors only
    frames = render.forest(SAMPLE)
    assert len(frames) > 1 and frames[0].tobytes() != frames[len(frames) // 2].tobytes()   # month names float
    assert len(render.character(SAMPLE)) == 1
    d = render.ImageDraw.Draw(render.Image.new("RGB", (1, 1)))
    t = render.fit(d, SAMPLE["quests"][0]["name"], render.PIXEL, 120)
    assert t.endswith("...") and d.textlength(t, font=render.PIXEL) <= 120
    lines = render.wrap(d, "cevdetbaranoral-portfolio", render.PIXEL, 40, 3)   # quest notes: break at hyphens, 3 lines max
    assert lines[0] == "cevdetbaranoral-"[: len(lines[0])] and 1 < len(lines) <= 3, lines
    assert all(d.textlength(l, font=render.PIXEL) <= 40 for l in lines), lines
    assert render.wrap(d, "winhub", render.PIXEL, 40, 3) == ["winhub"]
    c = render.Card("bg-character.png")
    label = c.row("Commits", "12,345", 0, 0, 48)                                 # big numbers must not collide with the label
    assert d.textlength(label, font=render.PIXEL) + 2 + d.textlength("12,345", font=render.PIXEL) <= 48, label


if __name__ == "__main__":
    test_data()
    test_render()
    print("all ok")

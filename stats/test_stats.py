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
    langs = data.languages([repo("a", langs=(("Python", 300), ("HTML", 100))), repo("b", langs=(("Python", 100),))])
    assert langs == [("Python", 0.8), ("HTML", 0.2)]
    qs = data.quests([repo("BaranDev"), repo("x", desc=None, lang=None, pushed="2026-09-28T23:00:00Z"), repo("y"), repo("z"), repo("w")],
                     "barandev", date(2026, 10, 1))
    assert [q["name"] for q in qs] == ["x", "y", "z"]         # profile repo skipped, 3 max
    assert qs[0] == {"name": "x", "desc": "", "lang": "", "days": 3}
    user = {"login": "barandev", "pullRequests": {"totalCount": 7},
            "repositories": {"totalCount": 2, "nodes": [repo("a", stars=3), repo("b", stars=4)]},
            "contributionsCollection": {"totalCommitContributions": 5, "contributionCalendar": {"weeks": [
                {"contributionDays": [day("2026-01-04", 1, "FIRST_QUARTILE"), day("2026-01-05", 3, "FOURTH_QUARTILE")]}]}},
            "history": hist}
    s = data.derive(user, date(2026, 1, 6))
    assert (s["total"], s["stars"], s["prs"], s["repos"], s["commits"]) == (7, 7, 7, 2, 5)  # 01-05 counted once
    assert s["days"] == [(0, 0, 1), (0, 1, 4)]              # 2026-01-04 is a Sunday -> row 0


SAMPLE = {"login": "barandev", "level": 18, "xp": 0.42, "total": 12345, "commits": 85, "prs": 197, "repos": 25, "stars": 12,
          "languages": [("TypeScript", 0.5), ("Python", 0.2), ("JavaScript", 0.15), ("C#", 0.1), ("HTML", 0.05)],
          "quests": [{"name": "a-very-long-repository-name-that-cannot-possibly-fit", "desc": "x" * 200, "lang": "TypeScript", "days": 0},
                     {"name": "winhub", "desc": "", "lang": "", "days": 36}],
          "days": [(c, r, (c * 7 + r) % 5) for c in range(53) for r in range(7)][:368], "current": 12, "longest": 40}


def test_render():
    allowed = render.palette() | {render.GOLD, render.EDGE}
    for s in (SAMPLE, dict(SAMPLE, languages=[], quests=[])):   # also an account with no languages or repos
        for fn in (render.character, render.quests, render.forest):
            im = fn(s)
            assert im.size == (1600, 640), fn.__name__
            stray = {c for _, c in im.getcolors(1 << 16)} - allowed
            assert not stray, (fn.__name__, list(stray)[:5])      # identical style: palette + title colors only
    d = render.ImageDraw.Draw(render.Image.new("RGB", (1, 1)))
    t = render.fit(d, SAMPLE["quests"][0]["name"], render.PIXEL, 120)
    assert t.endswith("...") and d.textlength(t, font=render.PIXEL) <= 120


if __name__ == "__main__":
    test_data()
    test_render()
    print("all ok")

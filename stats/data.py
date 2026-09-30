"""Fetch the profile's stats from the GitHub GraphQL API and derive the numbers the cards show."""
import json
import urllib.request
from datetime import date, datetime, timedelta

API = "https://api.github.com/graphql"
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

MAIN = """query($login: String!) { user(login: $login) {
  login createdAt pullRequests { totalCount }
  repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
               orderBy: {field: PUSHED_AT, direction: DESC}) {
    totalCount nodes { name description stargazerCount pushedAt primaryLanguage { name }
      languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } } }
  contributionsCollection { totalCommitContributions contributionCalendar {
    weeks { contributionDays { date contributionCount contributionLevel } } } } } }"""

YEAR = """query($login: String!, $from: DateTime!, $to: DateTime!) { user(login: $login) {
  contributionsCollection(from: $from, to: $to) { contributionCalendar {
    weeks { contributionDays { date contributionCount } } } } } }"""


def gql(query, token, **variables):
    req = urllib.request.Request(API, json.dumps({"query": query, "variables": variables}).encode(),
                                 {"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]["user"]


def fetch(login, token):
    """The main query plus one calendar per year since the account was created (a query spans a year at most)."""
    user = gql(MAIN, token, login=login)
    user["history"] = []
    for y in range(int(user["createdAt"][:4]), date.today().year + 1):
        cal = gql(YEAR, token, login=login, **{"from": f"{y}-01-01T00:00:00Z", "to": f"{y}-12-31T23:59:59Z"})
        user["history"] += [d for w in cal["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    return user


def counts(days):
    return {d["date"]: d["contributionCount"] for d in days}  # dict: a day repeated by two yearly queries counts once


def streaks(days, today):
    c = counts(days)
    longest = run = 0
    day, end = date.fromisoformat(min(c)), date.fromisoformat(max(c))
    while day <= end:
        run = run + 1 if c.get(day.isoformat()) else 0
        longest = max(longest, run)
        day += timedelta(days=1)
    current, day = 0, today if c.get(today.isoformat()) else today - timedelta(days=1)  # no contribution yet today is fine
    while c.get(day.isoformat()):
        current += 1
        day -= timedelta(days=1)
    return current, longest


def level(total):
    """Reaching level L+1 takes 25*L*(L+1) contributions, so each level costs 50 more than the one before."""
    lvl = 0
    while 25 * (lvl + 1) * (lvl + 2) <= total:
        lvl += 1
    return lvl + 1, round((total - 25 * lvl * (lvl + 1)) / (50 * (lvl + 1)), 4)


def languages(repos, top=5):
    sizes = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
    total = sum(sizes.values()) or 1
    return [(n, round(s / total, 4)) for n, s in sorted(sizes.items(), key=lambda kv: -kv[1])[:top]]


def quests(repos, login, today, n=3):
    """Most recently pushed repos, skipping the profile repo (the card workflow pushes it every day)."""
    out = []
    for r in repos:
        if r["name"].lower() == login.lower():
            continue
        pushed = datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00")).date()
        out.append({"name": r["name"], "desc": r["description"] or "",
                    "lang": (r["primaryLanguage"] or {}).get("name", ""), "days": (today - pushed).days})
    return out[:n]


def derive(user, today):
    repos = user["repositories"]["nodes"]
    coll = user["contributionsCollection"]
    total = sum(counts(user["history"]).values())
    lvl, xp = level(total)
    current, longest = streaks(user["history"], today)
    return {"login": user["login"], "level": lvl, "xp": xp, "total": total,
            "commits": coll["totalCommitContributions"], "prs": user["pullRequests"]["totalCount"],
            "repos": user["repositories"]["totalCount"], "stars": sum(r["stargazerCount"] for r in repos),
            "languages": languages(repos), "quests": quests(repos, user["login"], today),
            "days": [(col, (date.fromisoformat(d["date"]).weekday() + 1) % 7, LEVELS[d["contributionLevel"]])
                     for col, w in enumerate(coll["contributionCalendar"]["weeks"]) for d in w["contributionDays"]],
            "current": current, "longest": longest}

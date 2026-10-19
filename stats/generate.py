"""python stats/generate.py <out_dir>   (env: GITHUB_TOKEN, optional GITHUB_USER (default BaranDev) and BIRTHDATE YYYY-MM-DD)
Fetches the live stats and writes character.png, quests.png and forest.png. Any API error exits non-zero, so the
workflow publishes nothing and the previous cards stay live."""
import os
import sys
from datetime import date
from pathlib import Path

import data
import render

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
birth = date.fromisoformat(os.environ["BIRTHDATE"]) if os.environ.get("BIRTHDATE") else None  # private repo secret
s = data.derive(data.fetch(os.environ.get("GITHUB_USER", "BaranDev"), os.environ["GITHUB_TOKEN"]), date.today(), birth)
for name in ("character", "quests", "forest"):
    first, *rest = getattr(render, name)(s)
    # more than one frame -> animated PNG (APNG), which GitHub READMEs play inline
    first.save(out / f"{name}.png", optimize=True, save_all=bool(rest), append_images=rest, duration=180, loop=0)
print("wrote", out, "level", s["level"], "streak", s["current"])

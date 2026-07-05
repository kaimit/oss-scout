import re

import requests
from bs4 import BeautifulSoup

from . import db, github_api


def fetch_trending(language=None, since="daily"):
    """抓取 github.com/trending 页面（无官方 API，解析 HTML）。"""
    lang = "/" + language if language else ""
    url = "https://github.com/trending{}?since={}".format(lang, since)
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; oss-scout/0.1)"},
        timeout=30,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for art in soup.select("article.Box-row"):
        a = art.select_one("h2 a")
        if not a or not a.get("href"):
            continue
        repo = a["href"].strip("/")
        p = art.select_one("p")
        desc = p.get_text(strip=True) if p else ""
        stars = 0
        sa = art.select_one('a[href$="/stargazers"]')
        if sa:
            m = re.search(r"[\d,]+", sa.get_text())
            if m:
                stars = int(m.group().replace(",", ""))
        recent = 0
        m = re.search(
            r"([\d,]+)\s+stars?\s+(?:today|this week|this month)",
            art.get_text(" ", strip=True),
        )
        if m:
            recent = int(m.group(1).replace(",", ""))
        lang_el = art.select_one('[itemprop="programmingLanguage"]')
        out.append({
            "repo": repo,
            "description": desc[:300],
            "language": lang_el.get_text(strip=True) if lang_el else (language or ""),
            "stars": stars,
            "stars_recent": recent,
            "source": "trending/" + since,
        })
    return out


def discover(language=None, since="daily"):
    """优先抓 trending 页面；页面结构变化或被拒时回退到 search API。"""
    items = []
    try:
        items = fetch_trending(language, since)
    except Exception:
        pass
    if not items:
        days = {"daily": 7, "weekly": 30, "monthly": 90}.get(since, 7)
        found = github_api.search_recent(language=language, days=days)
        items = [{
            "repo": it["full_name"],
            "description": (it.get("description") or "")[:300],
            "language": it.get("language") or (language or ""),
            "stars": it.get("stargazers_count", 0),
            "stars_recent": 0,
            "source": "search/created>{}d".format(days),
        } for it in found]

    con = db.connect()
    with con:
        for it in items:
            row = dict(it)
            row["discovered_at"] = db.now()
            db.upsert_candidate(con, row)
    con.close()
    return items

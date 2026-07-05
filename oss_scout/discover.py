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


AGENT_TERMS = (
    "agent", "agentic", "llm", "autonomous", "copilot", "rag", "mcp",
    "assistant", "multi-agent", "chatbot", "openai", "anthropic", "langchain",
)


def is_agent_related(item):
    text = " ".join([
        item.get("repo", ""),
        item.get("description", ""),
        " ".join(item.get("topics", []) or []),
    ]).lower()
    return any(t in text for t in AGENT_TERMS)


def _from_search(found, source):
    return [{
        "repo": it["full_name"],
        "description": (it.get("description") or "")[:300],
        "language": it.get("language") or "",
        "stars": it.get("stargazers_count", 0),
        "stars_recent": 0,
        "topics": it.get("topics", []),
        "source": source,
    } for it in found]


def discover(language=None, since="daily", domain=None):
    """优先抓 trending 页面；结构变化或被拒时回退 search API。
    domain='agent' 时筛 trending 中的 agent 项目，并用 agent 定向搜索补充。"""
    items = []
    try:
        items = fetch_trending(language, since)
    except Exception:
        pass

    if domain == "agent":
        items = [it for it in items if is_agent_related(it)]
        try:
            days = {"daily": 14, "weekly": 30, "monthly": 90}.get(since, 14)
            items += _from_search(
                github_api.search_agents(language=language, days=days), "search/agent"
            )
        except Exception:
            pass
        seen, deduped = set(), []
        for it in items:
            if it["repo"] not in seen:
                seen.add(it["repo"])
                deduped.append(it)
        items = deduped
    elif not items:
        days = {"daily": 7, "weekly": 30, "monthly": 90}.get(since, 7)
        items = _from_search(
            github_api.search_recent(language=language, days=days),
            "search/created>{}d".format(days),
        )

    con = db.connect()
    with con:
        for it in items:
            row = {
                "repo": it["repo"],
                "description": it.get("description", ""),
                "language": it.get("language", ""),
                "stars": it.get("stars", 0),
                "stars_recent": it.get("stars_recent", 0),
                "source": it.get("source", ""),
                "discovered_at": db.now(),
            }
            db.upsert_candidate(con, row)
    con.close()
    return items

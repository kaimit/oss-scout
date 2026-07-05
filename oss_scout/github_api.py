import base64
from datetime import datetime, timedelta, timezone

import requests

from . import config

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


def _headers():
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "oss-scout/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if config.GITHUB_TOKEN:
        h["Authorization"] = "Bearer " + config.GITHUB_TOKEN
    return h


def get(path, **params):
    r = requests.get(API + path, headers=_headers(), params=params or None, timeout=30)
    if r.status_code in (403, 429) and "rate limit" in r.text.lower():
        raise GitHubError(
            "GitHub API 限流。在 .env 配置 GITHUB_TOKEN 可把额度从 60 提到 5000 次/小时"
        )
    if r.status_code == 404:
        raise GitHubError("仓库或资源不存在: " + path)
    r.raise_for_status()
    return r.json()


def repo_info(full):
    return get("/repos/" + full)


def readme(full):
    try:
        d = get("/repos/" + full + "/readme")
        return base64.b64decode(d.get("content", "")).decode("utf-8", "replace")
    except Exception:
        return ""


def top_issues(full, n=12):
    try:
        items = get(
            "/repos/" + full + "/issues",
            state="open", sort="comments", direction="desc", per_page=30,
        )
    except Exception:
        return []
    out = []
    for it in items:
        if "pull_request" in it:  # issues API 会混入 PR，剔除
            continue
        out.append({
            "number": it.get("number"),
            "title": it.get("title", ""),
            "comments": it.get("comments", 0),
            "body": (it.get("body") or "")[:600],
        })
        if len(out) >= n:
            break
    return out


def languages(full):
    try:
        return get("/repos/" + full + "/languages")
    except Exception:
        return {}


def file_tree(full, branch, limit=250):
    try:
        d = get("/repos/" + full + "/git/trees/" + branch, recursive=1)
    except Exception:
        return [], False
    paths = [t["path"] for t in d.get("tree", []) if t.get("type") == "blob"]
    return paths[:limit], bool(d.get("truncated")) or len(paths) > limit


def search_recent(language=None, days=7, min_stars=50, per_page=25):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    q = "created:>{} stars:>={}".format(since, min_stars)
    if language:
        q += ' language:"{}"'.format(language)
    d = get("/search/repositories", q=q, sort="stars", order="desc", per_page=per_page)
    return d.get("items", [])

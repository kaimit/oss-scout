import sqlite3
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    repo TEXT PRIMARY KEY,
    description TEXT DEFAULT '',
    language TEXT DEFAULT '',
    stars INTEGER DEFAULT 0,
    stars_recent INTEGER DEFAULT 0,
    source TEXT DEFAULT '',
    discovered_at TEXT DEFAULT '',
    status TEXT DEFAULT 'new'
)
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    config.ensure_dirs()
    con = sqlite3.connect(str(config.DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute(SCHEMA)
    return con


def upsert_candidate(con, c):
    con.execute(
        """INSERT INTO candidates (repo, description, language, stars, stars_recent, source, discovered_at)
           VALUES (:repo, :description, :language, :stars, :stars_recent, :source, :discovered_at)
           ON CONFLICT(repo) DO UPDATE SET
             description = excluded.description,
             language = excluded.language,
             stars = excluded.stars,
             stars_recent = excluded.stars_recent,
             source = excluded.source""",
        c,
    )


def set_status(con, repo, status):
    con.execute(
        "INSERT OR IGNORE INTO candidates (repo, discovered_at) VALUES (?, ?)",
        (repo, now()),
    )
    con.execute("UPDATE candidates SET status = ? WHERE repo = ?", (status, repo))


def list_candidates(con, limit=30):
    return con.execute(
        "SELECT * FROM candidates ORDER BY stars_recent DESC, stars DESC LIMIT ?",
        (limit,),
    ).fetchall()

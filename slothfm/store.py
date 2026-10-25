"""A small SQLite journal. Every notification is decided once, so a night can stop and resume anywhere."""
import json
import sqlite3

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  thread TEXT PRIMARY KEY, repo TEXT, private INTEGER, owner TEXT, reason TEXT, type TEXT, title TEXT,
  api_url TEXT, comment_url TEXT, unread INTEGER, updated TEXT, context TEXT,
  bucket TEXT, why TEXT, say TEXT, decided_by TEXT, model_ms INTEGER, sensitive INTEGER DEFAULT 0,
  tidied INTEGER DEFAULT 0, decided_at TEXT
);
"""


def db():
    config.HOME.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def upsert(items):
    """Add new notifications; a thread that changed since it was decided gets decided again."""
    con, fresh = db(), 0
    for it in items:
        row = con.execute("SELECT updated FROM items WHERE thread=?", (it["thread"],)).fetchone()
        if row and row["updated"] == it["updated"]:
            continue
        con.execute("""INSERT OR REPLACE INTO items (thread, repo, private, owner, reason, type, title, api_url,
                       comment_url, unread, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (it["thread"], it["repo"], int(it["private"]), it["owner"], it["reason"], it["type"], it["title"],
                     it["api_url"], it["comment_url"], int(it["unread"]), it["updated"]))
        fresh += 1
    con.commit()
    return fresh


def pending():
    return [r["thread"] for r in db().execute("SELECT thread FROM items WHERE bucket IS NULL ORDER BY updated DESC")]


def get(thread):
    r = db().execute("SELECT * FROM items WHERE thread=?", (thread,)).fetchone()
    d = dict(r)
    d["context"] = json.loads(d["context"]) if d.get("context") else {}
    return d


def decide(thread, bucket, why, say, decided_by, model_ms=0, sensitive=False, context=None):
    con = db()
    con.execute("""UPDATE items SET bucket=?, why=?, say=?, decided_by=?, model_ms=?, sensitive=?, context=?,
                   decided_at=datetime('now') WHERE thread=?""",
                (bucket, why, say, decided_by, model_ms, int(sensitive), json.dumps(context or {}), thread))
    con.commit()


def all_decided():
    rows = db().execute("SELECT * FROM items WHERE bucket IS NOT NULL ORDER BY updated DESC").fetchall()
    return [dict(r) for r in rows]


def mark_tidied(thread):
    con = db()
    con.execute("UPDATE items SET tidied=1 WHERE thread=?", (thread,))
    con.commit()


def supersede_ci():
    """Only the newest run of a workflow on a branch matters; older runs are decided as noise by code."""
    from .rules import ci_parts
    con, seen, n = db(), set(), 0
    rows = con.execute("SELECT thread, repo, title FROM items WHERE type='CheckSuite' AND bucket IS NULL ORDER BY updated DESC")
    for r in rows.fetchall():
        parts = ci_parts(r["title"])
        key = (r["repo"], parts.get("workflow"), parts.get("branch"))
        if None in key:
            continue
        if key in seen:
            decide(r["thread"], "noise", "an older run of the same workflow", None, "rule")
            n += 1
        seen.add(key)
    return n

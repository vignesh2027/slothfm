"""GitHub through the gh CLI, so Sloth FM never stores a token: it borrows the login you already have."""
import json
import re
import subprocess
from datetime import UTC, datetime, timedelta


def gh(path, method="GET", jq=None):
    cmd = ["gh", "api", "-X", method, path]
    if jq:
        cmd += ["--jq", jq]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode:
        raise RuntimeError(f"gh api {path}: {out.stderr.strip()[:200]}")
    return out.stdout


def notifications(days):
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cmd = ["gh", "api", "--paginate", f"notifications?all=true&per_page=50&since={since}", "--jq", ".[] | tojson"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True).stdout
    return [slim(json.loads(line)) for line in out.splitlines() if line.strip()]


def slim(n):
    repo = n["repository"]
    return {
        "thread": n["id"], "repo": repo["full_name"], "private": repo["private"], "owner": repo["owner"]["login"],
        "reason": n["reason"], "type": n["subject"]["type"], "title": n["subject"]["title"],
        "api_url": n["subject"]["url"], "comment_url": n["subject"].get("latest_comment_url"),
        "unread": n["unread"], "updated": n["updated_at"],
    }


def html_url(item):
    """The page a person would open for this notification."""
    url = item.get("api_url") or ""
    if url.startswith("https://api.github.com/repos/"):
        url = url.replace("https://api.github.com/repos/", "https://github.com/").replace("/pulls/", "/pull/")
        return url
    return f"https://github.com/{item['repo']}/actions" if item["type"] == "CheckSuite" else f"https://github.com/{item['repo']}"


def context(item):
    """What a person would glance at: the state of the thing and the last thing someone said."""
    ctx = {"repository_is_yours": item["owner"] == me_cached()}
    if item["type"] == "CheckSuite":
        from .rules import ci_parts
        ctx.update(ci_parts(item["title"]))
        ctx["triggered_by_your_push"] = item["reason"] == "ci_activity"
        ctx["default_branch"] = default_branch(item["repo"])
    if item.get("api_url") and item["type"] in ("PullRequest", "Issue"):
        try:
            d = json.loads(gh(item["api_url"]))
            ctx["state"] = d.get("state")
            ctx["merged"] = bool(d.get("merged"))
            ctx["opened_by"] = (d.get("user") or {}).get("login")
        except RuntimeError:
            pass
    if item.get("comment_url") and item.get("comment_url") != item.get("api_url"):
        try:
            c = json.loads(gh(item["comment_url"]))
            who = (c.get("user") or {}).get("login") or ""
            body = re.sub(r"<!--.*?-->", " ", c.get("body") or "", flags=re.S)
            ctx["last_comment_by"] = who
            ctx["last_comment_is_yours"] = who == me_cached()
            ctx["last_comment_is_from_a_bot"] = who.endswith("[bot]")
            ctx["last_comment"] = " ".join(body.split())[:600]
        except RuntimeError:
            pass
    return ctx


def me():
    return gh("user", jq=".login").strip()


_cache = {}


def me_cached():
    if "me" not in _cache:
        _cache["me"] = me()
    return _cache["me"]


def default_branch(repo):
    key = "branch:" + repo
    if key not in _cache:
        try:
            _cache[key] = gh(f"repos/{repo}", jq=".default_branch").strip()
        except RuntimeError:
            _cache[key] = ""
    return _cache[key]


def mark_read(thread):
    gh(f"notifications/threads/{thread}", method="PATCH")

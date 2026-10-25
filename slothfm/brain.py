"""The judgement, by Gemma running locally through Ollama. Nothing in your inbox leaves the laptop."""
import json
import re
import time
import urllib.request

from . import config

SYSTEM = """You triage one GitHub notification for an open-source developer while they sleep. You are given facts
about it as JSON. Choose one bucket:
- needs_you: someone or something is waiting on the developer. Examples: a review was requested from them; someone
  asked them a question or requested changes; a CLA check failed on their own branch or pull request (they must sign
  it); a workflow they triggered failed on their own branch or pull request; their repository's default branch is
  failing.
- good_news: something finished well (merged, approved, released, a fix landed).
- noise: nothing to do (CI on other people's default branches, releases they only watch, bots chatting, threads they
  merely follow, runs that were superseded).
Who spoke last matters: if last_comment_is_yours is true, the developer already answered and is waiting on others,
so it is not needs_you. A bot reporting a finished review with no findings is good_news.
"why": at most 12 words describing the notification itself, in plain English.
"say": one calm sentence of at most 22 words for a morning radio show, addressed to the developer as "you". Mention
the repository by its short name (repo_short). No URLs, no markdown, no names of the developer, no facts beyond
the JSON. Example: Your datadog-agent pull request is waiting on you to sign the contributor licence agreement."""

SCHEMA = {
    "type": "object",
    "properties": {
        "bucket": {"type": "string", "enum": ["needs_you", "good_news", "noise"]},
        "why": {"type": "string"},
        "say": {"type": "string"},
    },
    "required": ["bucket", "why", "say"],
}


def chat(messages, schema=None, temperature=0.0, num_predict=200):
    body = {"model": config.MODEL, "messages": messages, "stream": False,
            "options": {"temperature": temperature, "num_predict": num_predict}}
    if schema:
        body["format"] = schema
    req = urllib.request.Request(f"{config.OLLAMA}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as r:   # nosec B310: local Ollama only
        out = json.loads(r.read())
    return out["message"]["content"], int((time.perf_counter() - t0) * 1000)


def triage(item, ctx, me):
    facts = {
        "me": me, "repository": item["repo"], "repo_short": item["repo"].split("/")[-1], "kind": item["type"],
        "why_github_notified": item["reason"],
        "title": item["title"], "unread": bool(item["unread"]), **{k: v for k, v in ctx.items() if v},
    }
    text, ms = chat([{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": json.dumps(facts, ensure_ascii=False)}], schema=SCHEMA)
    d = json.loads(text)
    say = tidy_speech(d.get("say", ""), me)
    return d["bucket"], d.get("why", "")[:120], say[:220], ms


def tidy_speech(say, me=""):
    """Small models fall into a few awkward phrasings when told to say "you"; smooth the common ones."""
    say = " ".join(say.split()).replace("\u2019", "'")
    if me:
        say = re.sub(rf"\b{re.escape(me)}'s\b", "your", say, flags=re.IGNORECASE)
        say = re.sub(rf",?\s*{re.escape(me)},?", "", say, flags=re.IGNORECASE)
    say = re.sub(r"^You,? (?:have )?for (?:the )?(?:[\w.-]+/)?([\w.-]+?)(?: repo(?:sitory)?)?,\s*", r"In \1, you ", say)
    say = re.sub(r",?\s*you\.$", ".", say)
    say = say.replace("you have a", "you have a").replace("  ", " ").strip()
    return say[:1].upper() + say[1:]


def thought():
    """One unhurried line to end the show. Harmless, and the only creative liberty the model gets."""
    text, _ = chat([{"role": "user", "content": "Write one gentle sentence of sloth wisdom about doing less, "
                     "at most 16 words, no quotes, no emoji."}], temperature=0.9, num_predict=40)
    return " ".join(text.split()).strip('"')[:140]

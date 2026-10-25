"""Turn last night's decisions into the morning page and the radio show."""
import json
from datetime import datetime
from pathlib import Path

from . import brief, config, github, radio, store
from .brain import thought


def tidy_noise():
    """Mark noise as read on GitHub. Only with --tidy: the one action Sloth FM takes on your behalf."""
    n = 0
    for it in store.all_decided():
        if it["bucket"] == "noise" and it["unread"] and not it["tidied"]:
            github.mark_read(it["thread"])
            store.mark_tidied(it["thread"])
            n += 1
    return n


def make(tidy=False, public=False, out_dir: Path | None = None):
    items = store.all_decided()
    tidied = tidy_noise() if tidy else 0
    lines = radio.script(items, thought(), tidied > 0, github.me_cached())
    day = datetime.now().strftime("%Y-%m-%d")
    out = (out_dir or config.OUT) / day
    out.mkdir(parents=True, exist_ok=True)
    seconds = radio.speak(lines, out / "sloth-fm.mp3")
    model_minutes = sum(i["model_ms"] or 0 for i in items) / 60000
    (out / "script.txt").write_text("\n".join(lines) + "\n")
    (out / "index.html").write_text(brief.page(items, "sloth-fm.mp3", seconds, public=public, night={"minutes": model_minutes}))
    words_in = sum(len((i["title"] or "").split()) + len(json.loads(i["context"] or "{}").get("last_comment", "").split())
                   for i in items)
    (out / "stats.json").write_text(json.dumps({
        "notifications": len(items), "decided_by_code": sum(1 for i in items if i["decided_by"] == "rule"),
        "decided_by_gemma": sum(1 for i in items if i["decided_by"] == "gemma"),
        "buckets": {b: sum(1 for i in items if i["bucket"] == b) for b in ("needs_you", "good_news", "noise")},
        "gemma_minutes": round(model_minutes, 1), "show_seconds": seconds, "words_you_did_not_read": words_in,
        "tidied": tidied, "model": config.MODEL, "voice": config.VOICE}, indent=2))
    return out / "index.html"

"""The morning page: the two-line summary, the show, and every notification with its reason and a link."""
import base64
import html
from datetime import datetime
from pathlib import Path

from .github import html_url

LOGO = "data:image/svg+xml;base64," + base64.b64encode((Path(__file__).parent / "logo.svg").read_bytes()).decode()
TITLES = {"today": "Needs you today", "this_week": "Yours this week, nobody blocked", "good_news": "Good news",
          "noise": "Noise, safe to ignore"}


def two_lines(items):
    needs = [i for i in items if i["bucket"] == "needs_you" and i.get("urgency") == "today"]
    later = sum(1 for i in items if i["bucket"] == "needs_you" and i.get("urgency") != "today")
    good = sum(1 for i in items if i["bucket"] == "good_news")
    noise = sum(1 for i in items if i["bucket"] == "noise")
    first = (f"{len(needs)} of {len(items)} notifications need you today"
             + (": " + "; ".join((i["why"] or i["title"]).rstrip(".") for i in needs[:3]) + "." if needs else "."))
    return first, f"{later} can wait for this week, {good} went well and {noise} were noise."


def page(items, audio_name, seconds, public=False, night=None):
    def row(it):
        hidden = public and (it["sensitive"] or it["private"])
        title = "Private item, kept on the laptop" if hidden else html.escape(it["title"])
        repo = "" if hidden else html.escape(it["repo"])
        link = "" if hidden else f'<a href="{html.escape(html_url(it))}">open</a>'
        who = "code" if it["decided_by"] == "rule" else "Gemma"
        return (f'<li><div class="t">{title}</div><div class="m"><span>{repo}</span><span>{html.escape(it["why"] or "")}</span>'
                f'<span class="by">{who}</span>{link}</div></li>')

    l1, l2 = two_lines(items)
    blocks = []
    def section(i):
        if i["bucket"] == "needs_you":
            return "today" if i.get("urgency") == "today" else "this_week"
        return i["bucket"]

    for b in ("today", "this_week", "good_news", "noise"):
        group = [i for i in items if section(i) == b]
        blocks.append(f'<section class="{b}"><h2>{TITLES[b]} <small>{len(group)}</small></h2><ul>'
                      + "".join(row(i) for i in group) + "</ul></section>")
    stats = night or {}
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sloth FM morning</title><style>
:root{{--bg:#F4EFE6;--card:#FFFDF8;--ink:#2B2A26;--muted:#77705F;--moss:#5E7D4E;--sun:#D9822B;--line:#E4DCCB}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 ui-sans-serif,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:880px;margin:0 auto;padding:36px 18px 60px}}
.eyebrow{{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--moss);font-weight:700}}
h1{{font-size:30px;margin:6px 0 4px}}.lede{{font-size:19px;margin:14px 0 4px}}.lede2{{color:var(--muted);margin:0 0 18px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin:14px 0}}
audio{{width:100%}}.stats{{display:flex;gap:18px;flex-wrap:wrap;color:var(--muted);font-size:14px}}.stats b{{color:var(--ink)}}
h2{{font-size:18px;margin:26px 0 8px}}h2 small{{color:var(--muted);font-weight:500}}
ul{{list-style:none;padding:0;margin:0}}li{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:8px 0}}
.today li{{border-left:4px solid var(--sun)}}.this_week li{{border-left:4px solid #C9A86A}}.good_news li{{border-left:4px solid var(--moss)}}.noise li{{opacity:.75}}
.t{{font-weight:600;overflow-wrap:anywhere}}.m{{display:flex;gap:12px;flex-wrap:wrap;font-size:13.5px;color:var(--muted)}}
.by{{background:#EFE7D6;border-radius:999px;padding:0 8px}}a{{color:var(--sun)}}
</style></head><body><main>
<div style="display:flex;align-items:center;gap:14px"><img src="{LOGO}" alt="" width="56" height="56">
<div><div class="eyebrow">Sloth FM · {datetime.now().strftime('%A %d %B')}</div><h1 style="margin:2px 0 0">Good morning.</h1></div></div>
<p class="lede">{html.escape(l1)}</p><p class="lede2">{html.escape(l2)}</p>
<div class="card"><audio controls src="{html.escape(audio_name)}"></audio>
<div class="stats"><span>show <b>{seconds:.0f} s</b></span><span>read overnight <b>{len(items)}</b></span>
<span>decided by code <b>{sum(1 for i in items if i['decided_by'] == 'rule')}</b></span>
<span>decided by Gemma <b>{sum(1 for i in items if i['decided_by'] == 'gemma')}</b></span>
{f"<span>night shift <b>{stats.get('minutes', 0):.0f} min</b> on this laptop</span>" if stats else ""}</div></div>
{''.join(blocks)}
<p class="lede2" style="margin-top:28px">Read by Gemma on this laptop, spoken by Kokoro on this laptop. Nothing left the machine.</p>
</main></body></html>"""

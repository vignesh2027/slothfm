"""Activities: the parts of the night shift that touch GitHub, Gemma, the battery and the disk."""
from temporalio import activity

from . import brain, github, power, rules, store


@activity.defn
def collect(days: int) -> list[str]:
    fresh = store.upsert(github.notifications(days))
    older = store.supersede_ci()
    activity.logger.info("collected %s new or changed notifications; %s were older CI runs", fresh, older)
    return store.pending()


@activity.defn
def plugged_in() -> bool:
    return power.on_ac_power()


@activity.defn
def triage_one(thread: str) -> str:
    item = store.get(thread)
    me = github.me()
    ctx = github.context(item)
    secret = rules.sensitive(item)
    if item["type"] == "CheckSuite" and ctx.get("pull_request_title"):
        if store.pull_request_thread(item["repo"], ctx["pull_request_title"]):
            store.decide(thread, "noise", "CI on a pull request that has its own notification", None, "rule", 0, secret, ctx)
            return "noise"
    decided = rules.decide(item, ctx, me)
    if decided:
        bucket, why, say = decided
        urgency = "today" if bucket == "needs_you" else "none"
        store.decide(thread, bucket, why, say, "rule", 0, secret, ctx, urgency)
        return bucket
    bucket, why, say, ms, urgency = brain.triage(item, ctx, me)
    if bucket == "needs_you" and ctx.get("review_requested_from_you"):
        urgency = "today"                              # someone is blocked on your review: code overrides
    if bucket == "needs_you" and item["type"] == "CheckSuite":
        urgency = "this_week"                          # a red check on your branch blocks nobody else
    if secret:
        say = "There is a private item waiting for you. The details are on your morning page."
    store.decide(thread, bucket, why, say, "gemma", ms, secret, ctx, urgency)
    return bucket


@activity.defn
def morning(tidy: bool) -> str:
    from .morning import make
    return str(make(tidy=tidy))

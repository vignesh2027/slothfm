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
    decided = rules.decide(item, ctx, me)
    if decided:
        bucket, why, say = decided
        store.decide(thread, bucket, why, say, "rule", 0, secret, ctx)
        return bucket
    bucket, why, say, ms = brain.triage(item, ctx, me)
    if secret:
        say = "There is a private item waiting for you. The details are on your morning page."
    store.decide(thread, bucket, why, say, "gemma", ms, secret, ctx)
    return bucket


@activity.defn
def morning(tidy: bool) -> str:
    from .morning import make
    return str(make(tidy=tidy))

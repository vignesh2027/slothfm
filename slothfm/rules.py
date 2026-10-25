"""Code decides the obvious ones, so the model only spends time where a person would have to think.

Each rule returns (bucket, why, say) or None. Buckets:
  needs_you  - something waits on you
  good_news  - something finished well; worth one sentence
  noise      - nothing to do; safe to mark read
"""
import re

CI_PASSED = re.compile(r"\b(succeeded|passed|completed successfully)\b", re.IGNORECASE)
CI_CANCELLED = re.compile(r"\b(cancelled|canceled|skipped)\b", re.IGNORECASE)
CI_TITLE = re.compile(r"^(?:Run \w+: )?(?P<workflow>.+?)(?: workflow run| -) (?P<result>failed|succeeded|cancelled|completed)?"
                      r".*?for (?P<branch>\S+) branch", re.IGNORECASE)


def ci_parts(title):
    """Workflow, result and branch from a CI notification title, as far as GitHub states them."""
    m = CI_TITLE.search(title)
    return {k: v for k, v in (m.groupdict() if m else {}).items() if v}


def decide(item, ctx, me):
    t, title = item["type"], item["title"]
    if t == "RepositoryAdvisory":
        return ("needs_you", "a security advisory you are part of", "There is a security advisory waiting for you. "
                "I kept the details off the radio.")
    if t == "CheckSuite":
        if CI_PASSED.search(title):
            return ("noise", "a CI run passed", None)
        if CI_CANCELLED.search(title):
            return ("noise", "a CI run was cancelled", None)
        if ctx.get("pull_request_state") in ("merged", "closed"):
            return ("noise", f"CI on a pull request that is already {ctx['pull_request_state']}", None)
        return None                                   # a failure: is it yours to fix? the model reads it
    if t == "Release" and item["reason"] == "subscribed":
        return ("noise", "a new release of a repository you watch", None)
    if t in ("PullRequest", "Issue") and ctx.get("state") == "open" and ctx.get("whose_move") == "the maintainers'":
        return ("noise", "yours, but waiting on the maintainers", None)
    if t == "PullRequest" and ctx.get("merged"):
        return ("good_news", "your pull request was merged" if ctx.get("opened_by") == me else "a pull request was merged",
                None)
    return None


def sensitive(item):
    """Never read these aloud or put them on a page someone else might see."""
    return bool(item["private"]) or item["type"] == "RepositoryAdvisory"

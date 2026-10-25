from slothfm import radio, rules


def item(**kw):
    base = {"type": "PullRequest", "title": "t", "reason": "author", "private": 0, "repo": "o/r"}
    base.update(kw)
    return base


def test_ci_passed_and_releases_are_noise_without_the_model():
    assert rules.decide(item(type="CheckSuite", title="CI workflow run succeeded for main branch"), {}, "me")[0] == "noise"
    assert rules.decide(item(type="Release", reason="subscribed"), {}, "me")[0] == "noise"


def test_ci_failure_goes_to_the_model():
    assert rules.decide(item(type="CheckSuite", title="CLA Assistant workflow run failed for fix/x branch"), {}, "me") is None


def test_merged_pull_request_is_good_news():
    assert rules.decide(item(), {"merged": True, "opened_by": "me"}, "me")[:2] == ("good_news", "your pull request was merged")


def test_advisories_and_private_repos_are_sensitive_and_never_read_aloud():
    adv = item(type="RepositoryAdvisory", title="password can be recorded")
    bucket, _, say = rules.decide(adv, {}, "me")
    assert bucket == "needs_you" and "password" not in say
    assert rules.sensitive(adv) and rules.sensitive(item(private=1))


def test_the_show_states_counts_from_code_not_the_model():
    items = [{"bucket": "needs_you", "urgency": "today", "say": "Sign the CLA.", "why": "", "repo": "a/b", "type": "CheckSuite"},
             {"bucket": "needs_you", "urgency": "this_week", "say": "Fix CI.", "why": "", "repo": "a/b", "type": "CheckSuite"},
             {"bucket": "noise", "say": None, "why": "", "repo": "a/b", "type": "CheckSuite"},
             {"bucket": "noise", "say": None, "why": "", "repo": "a/b", "type": "Release"}]
    lines = radio.script(items, "Rest is work too.", tidied=False)
    text = " ".join(lines)
    assert "I read 4 GitHub notifications" in text and "1 thing needs you today" in text and "The other 2 were noise" in text
    assert "1 more are yours this week" in text and "Fix CI." not in text


def test_ci_on_a_merged_pull_request_is_noise():
    ci = item(type="CheckSuite", title="E2E Tests workflow run failed for fix/x branch")
    assert rules.decide(ci, {"pull_request_state": "merged"}, "me")[0] == "noise"
    assert rules.decide(ci, {"pull_request_state": "open"}, "me") is None


def test_whose_move_is_decided_by_facts():
    from slothfm.github import whose_move
    assert whose_move({"review_requested_from_you": True}) == "yours"
    assert whose_move({"you_opened_it": True, "last_comment_is_yours": True, "last_comment_by": "me"}) == "the maintainers'"
    assert whose_move({"you_opened_it": True, "last_comment_by": "maintainer"}) == "yours"
    pr = item()
    assert rules.decide(pr, {"state": "open", "whose_move": "the maintainers'"}, "me")[0] == "noise"


def test_public_page_hides_private_repositories():
    from slothfm import brief
    it = {"bucket": "noise", "urgency": None, "title": "secret-thing", "repo": "me/private-repo", "why": "x",
          "decided_by": "rule", "sensitive": 0, "private": 1, "type": "CheckSuite", "api_url": None}
    page = brief.page([it], "a.mp3", 1.0, public=True)
    assert "private-repo" not in page and "secret-thing" not in page

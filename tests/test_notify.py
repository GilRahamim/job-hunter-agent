from jobhunter.notify import notify_strong_matches, strong_matches

ROWS = [{"title": "ML Engineer", "company": "A", "score": 91.0}, {"title": "Dev", "company": "B", "score": 79.0},
        {"title": "AI Engineer", "company": "C", "score": 85.0}]


def test_disabled_sends_nothing():
    sent = []
    assert notify_strong_matches(ROWS, {"notify": {"enabled": False}}, lambda t, x: sent.append(t)) == 0
    assert notify_strong_matches(ROWS, {}, lambda t, x: sent.append(t)) == 0 and not sent


def test_announces_best_match_and_count():
    sent = []
    n = notify_strong_matches(ROWS, {"notify": {"enabled": True, "min_score": 80}}, lambda t, x: sent.append((t, x)))
    assert n == 2 and "2 new strong" in sent[0][0] and "ML Engineer @ A (91)" in sent[0][1] and "+1" in sent[0][1]
    assert [r["title"] for r in strong_matches(ROWS, 80)] == ["ML Engineer", "AI Engineer"]


def test_nothing_above_threshold_and_sender_failure_are_silent():
    assert notify_strong_matches(ROWS, {"notify": {"enabled": True, "min_score": 99}}, lambda t, x: 1 / 0) == 0

    def boom(t, x):
        raise OSError("no powershell")
    assert notify_strong_matches(ROWS, {"notify": {"enabled": True}}, boom) == 0

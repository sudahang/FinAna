def test_breaker_opens_after_threshold():
    from finana.datacore.base import CircuitBreaker

    clock = [0.0]
    br = CircuitBreaker(threshold=3, cooldown=300, time_func=lambda: clock[0])
    for _ in range(3):
        assert br.allow()
        br.record_failure()
    assert br.state == "open"
    assert not br.allow()


def test_breaker_half_open_then_close():
    from finana.datacore.base import CircuitBreaker

    clock = [0.0]
    br = CircuitBreaker(threshold=2, cooldown=10, time_func=lambda: clock[0])
    for _ in range(2):
        br.record_failure()
    clock[0] = 11.0
    assert br.state == "half-open"
    assert br.allow()
    br.record_success()
    assert br.state == "closed"


def test_breaker_reopens_on_half_open_failure():
    from finana.datacore.base import CircuitBreaker

    clock = [0.0]
    br = CircuitBreaker(threshold=1, cooldown=10, time_func=lambda: clock[0])
    br.record_failure()
    clock[0] = 11.0
    br.allow()
    br.record_failure()
    assert br.state == "open" and not br.allow()

from app.services import index_state


def test_reset_for_tests_clears_running_state() -> None:
    index_state.reset_for_tests()
    index_state.start()
    assert index_state.is_running() is True
    index_state.reset_for_tests()
    assert index_state.is_running() is False
    snapshot = index_state.snapshot()
    assert snapshot["status"] == "idle"

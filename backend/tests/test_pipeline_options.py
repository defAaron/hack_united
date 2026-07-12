from app.core.pipeline_options import ALLOWED_TARGET_DURATIONS, DEFAULT_TARGET_DURATION


def test_allowed_reel_lengths() -> None:
    assert ALLOWED_TARGET_DURATIONS == (30, 60, 90)
    assert DEFAULT_TARGET_DURATION == 90
    assert DEFAULT_TARGET_DURATION in ALLOWED_TARGET_DURATIONS

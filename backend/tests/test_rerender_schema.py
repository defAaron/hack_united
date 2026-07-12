from app.models.schemas import HighlightClip, RerenderRequest


def test_rerender_request_requires_at_least_one_clip() -> None:
    payload = RerenderRequest(
        clips=[
            HighlightClip(
                id="a",
                start_seconds=1.0,
                end_seconds=5.0,
                excitement_score=0.9,
            )
        ]
    )
    assert len(payload.clips) == 1
    assert payload.clips[0].id == "a"

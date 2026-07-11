from app.services.music_catalog import get_music_track, list_music_tracks, resolve_music_path


def test_list_music_tracks_includes_bundled_titles() -> None:
    tracks = list_music_tracks()
    titles = {track.title for track in tracks}
    assert "Vibehorn" in titles
    assert "The Mountain" in titles
    assert "Solarflex Hype" in titles
    assert "MFCC" in titles
    assert all(track.path.exists() for track in tracks)


def test_resolve_music_path_by_id() -> None:
    path = resolve_music_path("the-mountain")
    assert path is not None
    assert path.name == "the-mountain.mp3"
    assert get_music_track("missing-track") is None

import pytest
from src.services.m3u_parser import M3UParser
from src.services.stream_proxy import StreamProxyServer


# Qt imports require a QApplication; skip if headless
pytest.importorskip("PySide6")


def test_content_type_detection_by_url_patterns():
    assert M3UParser._detect_content_type("Movie", "Any", "https://example.com/movie/u/p/1.mp4") == "movie"
    assert M3UParser._detect_content_type("Series", "Any", "https://example.com/series/u/p/2.mp4") == "series"
    assert M3UParser._detect_content_type("Live", "Any", "https://example.com/live/u/p/3.ts") == "live"


def test_stream_proxy_rejects_unsafe_urls():
    proxy = StreamProxyServer()

    try:
        proxy.set_stream("file:///etc/passwd")
        assert False, "Expected ValueError for non-http stream"
    except ValueError:
        pass

    try:
        proxy.register_stream("http://localhost:8080/stream")
        assert False, "Expected ValueError for localhost stream"
    except ValueError:
        pass


def test_qt_views_import():
    """Verify migrated Qt views can be imported."""
    from src.qt_views import HubView, ContentView, PlayerView, SeriesView, SettingsView
    assert HubView is not None
    assert ContentView is not None
    assert PlayerView is not None
    assert SeriesView is not None
    assert SettingsView is not None


def test_qt_components_import():
    """Verify migrated Qt components can be imported."""
    from src.qt_components import VideoPlayerComponent
    assert VideoPlayerComponent is not None

from src.services.m3u_parser import M3UParser
from src.services.stream_proxy import StreamProxyServer


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

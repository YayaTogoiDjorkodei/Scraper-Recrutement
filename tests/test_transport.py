from pathlib import Path

from corporate_scraper.models import FetchOutcomeKind
from corporate_scraper.sources import LinkedInAdapter
from corporate_scraper.transport import HttpTransport, load_proxy_file, parse_proxy_line


class Response:
    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


class Session:
    def __init__(self, response): self.response = response; self.calls = []
    def get(self, url, **kwargs): self.calls.append((url, kwargs)); return self.response


def test_proxy_loader_keeps_aliases_and_never_returns_passwords(tmp_path):
    path = tmp_path / "proxies.txt"
    path.write_text("127.0.0.1:8080:user:secret\ninvalid\n", encoding="utf-8")
    routes, invalid = load_proxy_file(path)
    assert routes[0].alias == "127.0.0.1:8080"
    assert invalid == [2]
    assert "secret" not in routes[0].alias


def test_transport_reuses_explicit_proxy_without_silent_fallback():
    proxy = parse_proxy_line("127.0.0.1:8080:user:secret")
    session = Session(Response(200, "<ul><li><h3 class='base-search-card__title'>Python</h3><a class='base-card__full-link' href='/jobs/view/1'></a></li></ul>"))
    result = HttpTransport("TestAgent/1.0", proxy, session).fetch(LinkedInAdapter(), "https://example.test")
    assert result.outcome.kind == FetchOutcomeKind.SUCCESS
    assert result.proxy_alias == "127.0.0.1:8080"
    assert session.calls[0][1]["proxies"]["https"].endswith("@127.0.0.1:8080")


def test_transport_classifies_throttling_and_denial_before_parsing():
    adapter = LinkedInAdapter()
    throttled = HttpTransport("Agent", session=Session(Response(429, headers={"Retry-After": "30"}))).fetch(adapter, "https://example.test")
    denied = HttpTransport("Agent", session=Session(Response(403))).fetch(adapter, "https://example.test")
    assert (throttled.outcome.kind, throttled.outcome.retry_after_seconds) == (FetchOutcomeKind.THROTTLED, 30)
    assert denied.outcome.kind == FetchOutcomeKind.BLOCKED


def test_detail_transport_allows_a_valid_page_without_search_cards():
    result = HttpTransport("Agent", session=Session(Response(200, "<div class='description__text'>Python requis</div>"))).fetch_detail(
        LinkedInAdapter(), "https://example.test/jobs/view/1"
    )

    assert result.outcome.kind == FetchOutcomeKind.SUCCESS
    assert LinkedInAdapter().parse_description(result.html or "") == "Python requis"

"""Requests-first transport with session reuse and redacted proxy configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import requests

from .models import FetchOutcome, FetchOutcomeKind
from .sources import SourceAdapter


@dataclass(frozen=True, slots=True)
class ProxyRoute:
    host: str
    port: int
    username: str
    password: str

    @property
    def alias(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def requests_proxies(self) -> dict[str, str]:
        address = f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return {"http": address, "https": address}


def parse_proxy_line(line: str) -> ProxyRoute:
    """Accept the existing ``ip:port:user:password`` format without logging it."""
    values = line.strip().split(":", 3)
    if len(values) != 4 or not all(values):
        raise ValueError("A proxy must use ip:port:username:password format.")
    host, port_text, username, password = values
    try:
        port = int(port_text)
    except ValueError as error:
        raise ValueError("The proxy port must be a number.") from error
    if not 1 <= port <= 65_535:
        raise ValueError("The proxy port must be between 1 and 65535.")
    return ProxyRoute(host=host, port=port, username=username, password=password)


def load_proxy_file(path: str | Path) -> tuple[list[ProxyRoute], list[int]]:
    """Return valid routes and invalid line numbers, never credentials."""
    routes: list[ProxyRoute] = []
    invalid: list[int] = []
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return routes, invalid
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            routes.append(parse_proxy_line(line))
        except ValueError:
            invalid.append(number)
    return routes, invalid


@dataclass(frozen=True, slots=True)
class TransportResult:
    outcome: FetchOutcome
    html: str | None = None
    status_code: int | None = None
    proxy_alias: str | None = None


class RequestSession(Protocol):
    def get(self, url: str, *, headers: dict[str, str], timeout: int, proxies: dict[str, str] | None): ...


class HttpTransport:
    """A per-source worker owns one transport instance and its Requests session."""

    def __init__(self, user_agent: str, proxy: ProxyRoute | None = None, session: RequestSession | None = None,
                 timeout_seconds: int = 20) -> None:
        self.user_agent = user_agent
        self.proxy = proxy
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds

    def fetch(self, adapter: SourceAdapter, url: str) -> TransportResult:
        try:
            response = self.session.get(url, headers={"User-Agent": self.user_agent}, timeout=self.timeout_seconds,
                                        proxies=self.proxy.requests_proxies if self.proxy else None)
        except requests.RequestException as error:
            return TransportResult(FetchOutcome(FetchOutcomeKind.TRANSPORT_ERROR, type(error).__name__), proxy_alias=self._alias)
        status_code = response.status_code
        if status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
            return TransportResult(FetchOutcome(FetchOutcomeKind.THROTTLED, "HTTP 429", retry_seconds), status_code=status_code,
                                   proxy_alias=self._alias)
        if status_code in (401, 403):
            return TransportResult(FetchOutcome(FetchOutcomeKind.BLOCKED, f"HTTP {status_code}"), status_code=status_code,
                                   proxy_alias=self._alias)
        if status_code >= 500:
            return TransportResult(FetchOutcome(FetchOutcomeKind.TRANSPORT_ERROR, f"HTTP {status_code}"), status_code=status_code,
                                   proxy_alias=self._alias)
        if status_code >= 400:
            return TransportResult(FetchOutcome(FetchOutcomeKind.LAYOUT_ERROR, f"HTTP {status_code}"), status_code=status_code,
                                   proxy_alias=self._alias)
        outcome = adapter.classify(response.text)
        return TransportResult(outcome, response.text, status_code, self._alias)

    def fetch_detail(self, adapter: SourceAdapter, url: str) -> TransportResult:
        """Fetch a detail page without applying search-card classification.

        A valid detail page normally has no result cards, so using the search
        classifier here incorrectly converted readable descriptions into layout
        errors. The detail parser decides whether usable description text exists.
        """
        result = self.fetch(adapter, url)
        if result.status_code and 200 <= result.status_code < 300 and result.html is not None:
            return TransportResult(FetchOutcome(FetchOutcomeKind.SUCCESS, transport="http"), result.html,
                                   result.status_code, result.proxy_alias)
        return result

    @property
    def _alias(self) -> str | None:
        return self.proxy.alias if self.proxy else None

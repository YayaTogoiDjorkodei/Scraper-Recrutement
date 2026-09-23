"""Fixture-tested public-page adapters for LinkedIn and Indeed.

Selectors are isolated here because source markup changes frequently. They are
not treated as live verified until recorded in the consolidated v2 plan.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .models import FetchOutcome, FetchOutcomeKind, JobObservation
from .text import description_text


def _text(element) -> str | None:
    return element.get_text(" ", strip=True) if element else None


def _canonical_link(url: str, source: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    if source == "linkedin":
        # Public job links occur in both numeric and title-slug-plus-ID forms.
        match = re.search(r"/jobs/view/(?:.*-)?(\d+)/?$", parsed.path)
        key = match.group(1) if match else urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")), key
    query = parse_qs(parsed.query)
    key = query.get("jk", [urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))])[0]
    canonical_query = urlencode({"jk": key}) if key else ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, canonical_query, "")), key


class SourceAdapter(ABC):
    source: str
    base_url: str

    @abstractmethod
    def search_url(self, query: str, location: str, start: int) -> str: ...

    @abstractmethod
    def parse_search(self, html: str) -> list[JobObservation]: ...

    @abstractmethod
    def parse_description(self, html: str) -> str | None: ...

    def public_contact_pages(self, html: str, job_url: str) -> tuple[tuple[str, str], ...]:
        """Return explicitly linked public profile/company pages, in that order.

        These are only leads for visible business emails. The engine never
        guesses an address and never opens private account contact panels.
        """
        soup = BeautifulSoup(html or "", "lxml")
        candidates: list[tuple[str, str]] = []
        for link in soup.select("a[href]"):
            href = urljoin(job_url, link.get("href", ""))
            lowered = href.casefold()
            if "/in/" in lowered and href.startswith(("https://", "http://")):
                candidates.append(("public_poster", href))
                break
        for script in soup.select("script[type='application/ld+json']"):
            try:
                payload = json.loads(script.string or script.get_text())
            except (TypeError, json.JSONDecodeError):
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict) or "JobPosting" not in _types(item):
                    continue
                organization = item.get("hiringOrganization")
                if not isinstance(organization, dict):
                    continue
                for value in (organization.get("url"), organization.get("sameAs")):
                    values = value if isinstance(value, list) else (value,)
                    for candidate in values:
                        if isinstance(candidate, str) and candidate.startswith(("https://", "http://")):
                            candidates.append(("company_site", candidate))
                            break
                    if candidates and candidates[-1][0] == "company_site":
                        break
                if candidates and candidates[-1][0] == "company_site":
                    break
        return tuple(dict.fromkeys(candidates))

    @abstractmethod
    def _cards(self, soup: BeautifulSoup): ...

    def classify(self, html: str) -> FetchOutcome:
        soup = BeautifulSoup(html or "", "lxml")
        if soup.select("iframe[src*='captcha'], iframe[src*='challenge'], [data-sitekey], [data-testid*='captcha']"):
            return FetchOutcome(FetchOutcomeKind.BLOCKED, "Interactive challenge detected")
        page_text = soup.get_text(" ", strip=True).casefold()
        if "verify you are human" in page_text or "verify you're human" in page_text:
            return FetchOutcome(FetchOutcomeKind.BLOCKED, "Human verification detected")
        if self._cards(soup):
            return FetchOutcome(FetchOutcomeKind.SUCCESS)
        if any(marker in page_text for marker in ("no jobs found", "aucune offre", "aucun emploi", "0 job")):
            return FetchOutcome(FetchOutcomeKind.EMPTY)
        return FetchOutcome(FetchOutcomeKind.LAYOUT_ERROR, "Expected result cards were not found")

    @staticmethod
    def _description_from_json_ld(soup: BeautifulSoup) -> str | None:
        for script in soup.select("script[type='application/ld+json']"):
            try:
                payload = json.loads(script.string or script.get_text())
            except (TypeError, json.JSONDecodeError):
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if "JobPosting" in _types(item) and isinstance(item.get("description"), str):
                    return description_text(item["description"])
        return None


def _types(item: dict) -> tuple[str, ...]:
    value = item.get("@type", ())
    return (value,) if isinstance(value, str) else tuple(value) if isinstance(value, list) else ()


class LinkedInAdapter(SourceAdapter):
    source = "linkedin"
    base_url = "https://www.linkedin.com/jobs/search/"

    def search_url(self, query: str, location: str, start: int) -> str:
        return f"{self.base_url}?{urlencode({'keywords': query, 'location': location, 'start': start})}"

    def _cards(self, soup: BeautifulSoup):
        return soup.select("li:has(.base-search-card__title)")

    def parse_search(self, html: str) -> list[JobObservation]:
        soup = BeautifulSoup(html, "lxml")
        observations: list[JobObservation] = []
        for card in self._cards(soup):
            link = card.select_one("a.base-card__full-link")
            title = _text(card.select_one(".base-search-card__title"))
            if not link or not title or not link.get("href"):
                continue
            canonical_url, key = _canonical_link(urljoin(self.base_url, link["href"]), self.source)
            observations.append(JobObservation(source=self.source, source_key=key, canonical_url=canonical_url, title=title,
                                               company=_text(card.select_one(".base-search-card__subtitle")),
                                               location=_text(card.select_one(".job-search-card__location")),
                                               posted_text=_text(card.select_one("time"))))
        return observations

    def parse_description(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")
        structured = self._description_from_json_ld(soup)
        if structured:
            return structured
        element = soup.select_one(".show-more-less-html__markup, .description__text")
        return description_text(str(element)) if element else None


class IndeedAdapter(SourceAdapter):
    source = "indeed"
    base_url = "https://ma.indeed.com/jobs"

    def search_url(self, query: str, location: str, start: int) -> str:
        return f"{self.base_url}?{urlencode({'q': query, 'l': location, 'start': start})}"

    def _cards(self, soup: BeautifulSoup):
        return soup.select("div.job_seen_beacon, div.cardOutline")

    def parse_search(self, html: str) -> list[JobObservation]:
        soup = BeautifulSoup(html, "lxml")
        observations: list[JobObservation] = []
        for card in self._cards(soup):
            link = card.select_one("a.jcs-JobTitle")
            title = _text(card.select_one("h2.jobTitle"))
            if not link or not title or not link.get("href"):
                continue
            canonical_url, key = _canonical_link(urljoin(self.base_url, link["href"]), self.source)
            observations.append(JobObservation(source=self.source, source_key=key, canonical_url=canonical_url, title=title,
                                               company=_text(card.select_one("span.companyName, [data-testid='company-name']")),
                                               location=_text(card.select_one("div.companyLocation, [data-testid='text-location']")),
                                               posted_text=_text(card.select_one("span.date, [data-testid='myJobsStateDate']"))))
        return observations

    def parse_description(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")
        structured = self._description_from_json_ld(soup)
        if structured:
            return structured
        element = soup.select_one("#jobDescriptionText, .jobsearch-JobComponent-description")
        return description_text(str(element)) if element else None

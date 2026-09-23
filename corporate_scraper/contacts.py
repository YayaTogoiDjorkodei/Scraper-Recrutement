"""Public work-contact extraction with no address guessing or private-data access."""

from __future__ import annotations

from dataclasses import dataclass
import html
import re
from urllib.parse import urlsplit

from .text import description_text


EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[A-Z0-9][A-Z0-9._%+-]{0,63}@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+(?![\w.-])", re.IGNORECASE)
IGNORED_LOCAL_PARTS = frozenset({"noreply", "no-reply", "donotreply", "example", "test"})


@dataclass(frozen=True, slots=True)
class PublicContact:
    email: str
    level: str
    url: str
    confidence: int


SOURCE_CONFIDENCE = {
    "job_post": 100,
    "recruiter_linkedin_profile": 88,
    "company_linkedin_profile": 85,
    "company_website": 82,
    "company_contact_page": 90,
}


def public_email(text_or_html: str, level: str, url: str) -> PublicContact | None:
    """Return one visibly published work email, never an inferred address."""
    text = html.unescape(text_or_html or "")
    searchable = description_text(text) or text
    for match in EMAIL_PATTERN.finditer(searchable):
        email = match.group(0).rstrip(".,;:!?)]]}").casefold()
        local_part = email.partition("@")[0]
        if local_part not in IGNORED_LOCAL_PARTS:
            confidence = SOURCE_CONFIDENCE.get(level, 70)
            email_domain = email.rsplit("@", 1)[1]
            page_domain = urlsplit(url).hostname or ""
            if page_domain.casefold().removeprefix("www.") == email_domain.casefold().removeprefix("www."):
                confidence = min(100, confidence + 7)
            return PublicContact(email, level, url, confidence)
    return None

"""Public work-contact extraction with no address guessing or private-data access."""

from __future__ import annotations

from dataclasses import dataclass
import html
import re

from .text import description_text


EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[A-Z0-9][A-Z0-9._%+-]{0,63}@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+(?![\w.-])", re.IGNORECASE)
IGNORED_LOCAL_PARTS = frozenset({"noreply", "no-reply", "donotreply", "example", "test"})


@dataclass(frozen=True, slots=True)
class PublicContact:
    email: str
    level: str
    url: str


def public_email(text_or_html: str, level: str, url: str) -> PublicContact | None:
    """Return one visibly published work email, never an inferred address."""
    text = html.unescape(text_or_html or "")
    searchable = description_text(text) or text
    for match in EMAIL_PATTERN.finditer(searchable):
        email = match.group(0).rstrip(".,;:!?)]]}").casefold()
        local_part = email.partition("@")[0]
        if local_part not in IGNORED_LOCAL_PARTS:
            return PublicContact(email, level, url)
    return None

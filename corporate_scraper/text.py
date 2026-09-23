"""Normalize source markup into readable text without losing paragraph boundaries."""
from html import unescape
import re

from bs4 import BeautifulSoup


def description_text(value: str) -> str:
    text = value or ""
    # JSON-LD can contain HTML escaped once or twice. Decode before parsing.
    for _ in range(3):
        decoded = unescape(text)
        if decoded == text:
            break
        text = decoded
    if re.search(r"</?[a-z][^>]*>", text, re.I):
        soup = BeautifulSoup(text, "lxml")
        for element in soup.select("script, style, noscript"):
            element.decompose()
        for element in soup.find_all(["br", "p", "li", "div", "h1", "h2", "h3", "h4", "tr"]):
            element.insert_before("\n")
            element.insert_after("\n")
        text = soup.get_text()
    text = text.replace("\xa0", " ")
    return "\n".join(re.sub(r"[^\S\n]+", " ", line).strip()
                     for line in text.splitlines() if line.strip())

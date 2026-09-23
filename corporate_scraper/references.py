"""Versioned technology vocabulary used by the v2 extraction engine."""

from __future__ import annotations

from .extraction import ReferenceTerm


# The established local vocabulary remains the baseline. Deduplication keeps
# extraction deterministic while preserving the original product vocabulary.
from liste import technologies as _legacy_technologies


TECHNOLOGY_REFERENCES = tuple(
    ReferenceTerm(term, fuzzy=False) for term in sorted(set(item.strip() for item in _legacy_technologies if item.strip()), key=str.casefold)
)

# Explicit aliases cover common source spellings; do not fuzzy-match ordinary
# prose into technologies (for example "rest" into "Rust").
_ALIASES = {
    "JavaScript": ("JS",), "TypeScript": ("TS",), ".NET": ("dotnet",),
    "ASP.NET": ("ASP.NET Core",), "React": ("React.js", "ReactJS"),
    "Vue.js": ("Vue", "VueJS"), "Node.js": ("NodeJS",),
    "Microsoft SQL Server": ("MSSQL", "SQL Server"),
    "Microsoft 365": ("Office 365", "M365"), "CI/CD": ("CI/CD",),
    "Amazon SES": ("AWS SES",), "Chef Infra": ("Chef Infra",),
}
_known = {term.canonical.casefold(): term for term in TECHNOLOGY_REFERENCES}
for _generic in ("SES", "Chef", "Performance", "Security", "Systems", "Programming", "Infrastructure"):
    _known.pop(_generic.casefold(), None)
for _name, _aliases in _ALIASES.items():
    for _alias in _aliases:
        if _alias.casefold() != _name.casefold():
            _known.pop(_alias.casefold(), None)
    _known[_name.casefold()] = ReferenceTerm(_name, _aliases, fuzzy=False)
TECHNOLOGY_REFERENCES = tuple(_known.values())

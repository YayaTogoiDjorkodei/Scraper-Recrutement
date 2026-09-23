"""Evidence-bearing requirement matching for full job descriptions."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from functools import lru_cache

from rapidfuzz import fuzz

from .models import FieldEvidence, FilterSpec
from .text import description_text


@dataclass(frozen=True, slots=True)
class ReferenceTerm:
    canonical: str
    aliases: tuple[str, ...] = ()
    fuzzy: bool = True

    @property
    def phrases(self) -> tuple[str, ...]:
        return (self.canonical, *self.aliases)


def normalize(text: str) -> str:
    """Case-fold text while retaining symbols that distinguish technical terms."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


@lru_cache(maxsize=4096)
def _pattern(phrase: str, allow_short: bool = False) -> re.Pattern[str] | None:
    normalized = normalize(phrase).strip()
    # Isolated C, CI and similar short labels have too little evidence. C#, C++,
    # .NET and terms with at least three letters remain safely detectable.
    alphanumeric = "".join(char for char in normalized if char.isalnum())
    if len(alphanumeric) < 3 and normalized not in {"c#", "c++", ".net"} and not allow_short:
        return None
    left_boundary = r"[a-z0-9+#.]" if len(normalized) <= 2 else r"[a-z0-9+#]"
    return re.compile(rf"(?<!{left_boundary}){re.escape(normalized)}(?![a-z0-9+#])", re.IGNORECASE)


def _sentences(text: str) -> list[str]:
    values = [part.strip() for part in re.split(r"\n+|(?<=[.!?;])\s+", text) if part.strip()]
    return values or [text]


def _fuzzy_candidates(normalized_sentence: str, phrase: str) -> list[str]:
    """Return word spans comparable to a phrase without substring matching."""
    words = re.findall(r"[a-z0-9+#.]+", normalized_sentence)
    width = len(re.findall(r"[a-z0-9+#.]+", phrase))
    if not width:
        return []
    return [" ".join(words[index:index + width]) for index in range(len(words) - width + 1)]


def extract_requirements(text: str, references: tuple[ReferenceTerm, ...], threshold: int = 90,
                         field: str = "skill_required", rule_version: str = "v1") -> tuple[FieldEvidence, ...]:
    """Return one explainable evidence item per canonical requirement.

    Exact/alias matches take precedence. Fuzzy matching is limited to longer
    phrases, operates per sentence, and never turns a near miss into an exact
    value without recording its score and source excerpt.
    """
    threshold = max(80, threshold)
    sentences = _sentences(text)
    normalized_sentences = [(sentence, normalize(sentence)) for sentence in sentences]
    found: list[FieldEvidence] = []
    for reference in references:
        if reference.canonical in {"SOLID", "REST", "ARM"} and not re.search(rf"\b{reference.canonical}\b", text):
            continue
        exact_match: FieldEvidence | None = None
        eligible_for_fuzzy = False
        for phrase in reference.phrases:
            pattern = _pattern(phrase, allow_short=phrase != reference.canonical)
            if pattern is None:
                continue
            if len("".join(char for char in normalize(phrase) if char.isalnum())) >= 4:
                eligible_for_fuzzy = True
            for sentence, normalized_sentence in normalized_sentences:
                if pattern.search(normalized_sentence):
                    method = "exact" if normalize(phrase) == normalize(reference.canonical) else "alias"
                    exact_match = FieldEvidence(field, reference.canonical, sentence, method, 100.0, rule_version)
                    break
            if exact_match:
                break
        if exact_match:
            found.append(exact_match)
            continue
        if not reference.fuzzy or not eligible_for_fuzzy:
            continue
        best_score = 0.0
        best_sentence = ""
        for phrase in reference.phrases:
            normalized_phrase = normalize(phrase)
            if len("".join(char for char in normalized_phrase if char.isalnum())) < 4:
                continue
            for sentence, normalized_sentence in normalized_sentences:
                for candidate in _fuzzy_candidates(normalized_sentence, normalized_phrase):
                    score = fuzz.ratio(normalized_phrase, candidate)
                    if score > best_score:
                        best_score, best_sentence = score, sentence
        if best_score >= threshold:
            found.append(FieldEvidence(field, reference.canonical, best_sentence, "fuzzy", best_score, rule_version))
    return tuple(found)


_PATTERN_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("education", re.compile(r"\b(?:bac\s*\+\s*[2-8](?:\s*(?:/|ou|à)\s*\+?\s*[2-8])?|bts|dut|licence|doctorat|ph\.?d\.?|bachelor(?:[’']s)?(?:\s+degree)?|master(?:[’']s)?(?:\s+degree)?|dipl[oô]me\s+d[’']ing[ée]nieur|engineering\s+degree)\b", re.IGNORECASE)),
    ("experience", re.compile(r"\b(?:minimum\s+(?:de\s+)?|au moins\s+|plus de\s+|at least\s+)?\d+\s*(?:\+|(?:à|a|to|[-–])\s*\d+)?\s*(?:ans?|années?|years?|yrs?)(?:\s+(?:d[’']exp[ée]rience|of\s+(?:professional\s+)?experience|experience))?\b", re.IGNORECASE)),
    ("contract", re.compile(r"\b(?:cdi|cdd|freelance|stage|alternance|internship|apprenticeship)\b", re.IGNORECASE)),
    ("work_schedule", re.compile(r"\b(?:temps plein|temps partiel|full[- ]time|part[- ]time)\b", re.IGNORECASE)),
    ("language", re.compile(r"\b(?:fran[çc]ais|anglais|arab(?:e|ic)|espagnol|english|french|spanish|german|allemand)\b", re.IGNORECASE)),
    ("work_mode", re.compile(r"\b(?:hybride|t[ée]l[ée]travail|remote|[àa] distance|pr[ée]sentiel)\b", re.IGNORECASE)),
)


def extract_structured_requirements(text: str, references: tuple[ReferenceTerm, ...],
                                    rule_version: str = "v3") -> tuple[FieldEvidence, ...]:
    """Extract skills plus explicitly stated qualification facts with excerpts.

    This deliberately reports only text that is present. It does not infer a
    diploma from a job title or an experience band from seniority labels.
    """
    text = description_text(text)
    evidence: list[FieldEvidence] = []
    preferred_section = False
    for sentence in _sentences(text):
        heading = normalize(sentence).strip(" :")
        if heading in {"nice to have", "atouts", "preferred skills", "qualifications souhaitees"}:
            preferred_section = True
        elif heading in {"must have", "requirements", "qualifications", "responsibilities", "missions", "profil recherche"}:
            preferred_section = False
        preferred = preferred_section or bool(re.search(r"\b(?:souhaite\w*|atout|apprecie\w*|preferred|nice to have|un plus)\b", heading))
        skill_field = "skill_preferred" if preferred else "skill_required"
        evidence.extend(extract_requirements(sentence, references, field=skill_field, rule_version=rule_version))
        for field, pattern in _PATTERN_RULES:
            for match in pattern.finditer(sentence):
                context = normalize(sentence)
                if field == "experience" and not re.search(r"experience|experiences|expérience|expériences", context):
                    continue
                if field == "experience" and re.search(r"\b(?:we provide|we have|our company|notre entreprise|notre societe|nous accompagnons)\b", context):
                    continue
                if field == "contract" and normalize(match.group(0)) == "stage":
                    if not (context.strip(" .:-") == "stage" or re.search(r"stage\s+(?:remunere|pfe|de fin|en |[-–—])|(?:contrat|offre|proposons|propose)\s*(?:de|:)?\s*stage", context)):
                        continue
                if field == "contract" and normalize(match.group(0)) == "cdd" and re.search(r"autosar|mcal|bsw|driver", context):
                    continue
                if field == "education" and normalize(match.group(0)) == "master" and re.search(r"scrum\s+master|master\s+data", context):
                    continue
                value = re.sub(r"\s+", " ", match.group(0)).strip()
                evidence.append(FieldEvidence(field, value, sentence, "pattern", 100.0, rule_version))
    # A repeated term in several sentences is useful source text but redundant
    # in a review table. Keep its first occurrence deterministically.
    unique: dict[tuple[str, str], FieldEvidence] = {}
    for item in evidence:
        unique.setdefault((item.field, normalize(item.value)), item)
    return tuple(unique.values())


def requirement_summary(evidence: tuple[FieldEvidence, ...]) -> dict[str, str | tuple[str, ...]]:
    """One projection for persistence, tables and Excel; fuzzy candidates stay reviewable."""
    def values(*fields: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.value for item in evidence
                                   if item.field in fields and item.method != "fuzzy"))
    return {"skills": values("skill_required", "skill_preferred"),
            "education": "; ".join(values("education")),
            "experience": "; ".join(values("experience")),
            "contract": "; ".join(values("contract")),
            "languages": "; ".join(values("language"))}


def evaluate_filters(evidence: tuple[FieldEvidence, ...], filters: FilterSpec) -> str:
    """Return ``matching``, ``excluded``, or ``unknown`` for explicit filters.

    Missing source text is never invented. Callers decide whether unknown values
    may count toward their target with ``include_unknown``.
    """
    requested = {
        "skill": tuple(filters.skills), "contract": (filters.contract,) if filters.contract else (),
        "education": (filters.education,) if filters.education else (),
        "experience": (filters.experience,) if filters.experience else (),
    }
    if not any(requested.values()):
        return "matching"
    observed: dict[str, list[str]] = {key: [] for key in requested}
    for item in evidence:
        if item.field in ("skill_required", "skill_preferred"):
            observed["skill"].append(item.value)
        elif item.field in observed:
            observed[item.field].append(item.value)
    unknown = False
    for field, wanted_values in requested.items():
        if not wanted_values:
            continue
        values = observed[field]
        if not values:
            unknown = True
            continue
        for wanted in wanted_values:
            wanted_normalized = normalize(wanted)
            if field == "education":
                wanted_normalized = re.sub(r"\s*\+\s*", "+", wanted_normalized)
                values = [re.sub(r"\s*\+\s*", "+", value) for value in values]
            if not any(wanted_normalized in normalize(value) for value in values):
                return "excluded"
    if unknown:
        return "matching" if filters.include_unknown else "unknown"
    return "matching"

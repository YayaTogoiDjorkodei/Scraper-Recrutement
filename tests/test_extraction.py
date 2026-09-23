from corporate_scraper.extraction import ReferenceTerm, evaluate_filters, extract_requirements, extract_structured_requirements
from corporate_scraper.models import FilterSpec


REFERENCES = (
    ReferenceTerm("Java"), ReferenceTerm("JavaScript", aliases=("JS",)), ReferenceTerm("Python"),
    ReferenceTerm("C"), ReferenceTerm("C#"), ReferenceTerm("C++"), ReferenceTerm(".NET"),
)


def values(text: str, threshold: int = 90):
    return {item.value: item for item in extract_requirements(text, REFERENCES, threshold=threshold)}


def test_exact_matching_does_not_confuse_java_with_javascript_or_short_tokens():
    result = values("Compétence requise : JavaScript, C#, C++ et .NET.")
    assert set(result) == {"JavaScript", "C#", "C++", ".NET"}
    assert result["JavaScript"].method == "exact"


def test_alias_and_fuzzy_matches_retain_their_evidence_method():
    alias = values("Une très bonne connaissance de JS est demandée.")
    fuzzy = values("Une expérience avec Pythom est demandée.", threshold=80)
    assert alias["JavaScript"].method == "alias"
    assert fuzzy["Python"].method == "fuzzy"
    assert fuzzy["Python"].score >= 80


def test_short_references_are_not_fuzzy_or_substring_matches():
    assert values("La certification CI/CD est un avantage.", threshold=1) == {}


def test_structured_extraction_keeps_explicit_qualification_evidence():
    result = extract_structured_requirements(
        "Python et Docker requis. Kubernetes est un atout. Bac+5 en informatique. "
        "Minimum de 3 à 5 ans d'expérience. CDI, travail hybride. Français et anglais courants.",
        (ReferenceTerm("Python"), ReferenceTerm("Docker"), ReferenceTerm("Kubernetes")),
    )
    fields = {(item.field, item.value.casefold()) for item in result}
    assert ("skill_required", "python") in fields
    assert ("skill_preferred", "kubernetes") in fields
    assert ("education", "bac+5") in fields
    assert ("experience", "minimum de 3 à 5 ans d'expérience") in fields
    assert ("contract", "cdi") in fields
    assert ("work_mode", "hybride") in fields
    assert ("language", "anglais") in fields


def test_explicit_filters_separate_matching_unknown_and_excluded_values():
    evidence = extract_structured_requirements("Python requis. CDI.", (ReferenceTerm("Python"),))
    assert evaluate_filters(evidence, FilterSpec(skills=("Python",), contract="CDI")) == "matching"
    assert evaluate_filters(evidence, FilterSpec(education="Bac+5")) == "unknown"
    assert evaluate_filters(evidence, FilterSpec(education="Bac+5", include_unknown=True)) == "matching"
    assert evaluate_filters(evidence, FilterSpec(contract="CDD")) == "excluded"

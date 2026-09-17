import ast
import hashlib
import json
import re

import liste
import reference_overrides
from tests.legacy_harness import FIXTURES, ROOT, OfflineTestCase, canonical_records, fixture, load_functions


class BaselineTests(OfflineTestCase):
    @staticmethod
    def _stable_text(value):
        # The legacy Normaliser currently emits replacement characters for
        # accented fixture text. Keep that behavior under test without making
        # the JSON encoding of the snapshot significant.
        if not isinstance(value, str):
            return value
        return re.sub(r"(?:<accent>)+", "<accent>", "".join(ch if ord(ch) < 128 else "<accent>" for ch in value))

    @classmethod
    def _stable_records(cls, records):
        return [{key: cls._stable_text(value) if isinstance(value, str) else
                 [cls._stable_text(item) for item in value] if isinstance(value, list) else value
                 for key, value in row.items()} for row in records]

    def test_recovered_vocabulary_matches_historical_fingerprint(self):
        values = dict(technologies=sorted(liste.technologies), niveaux_etudes=liste.niveaux_etudes,
                      experience=liste.experience, type_contrat=liste.type_contrat)
        digest = hashlib.sha256(json.dumps(values, ensure_ascii=True, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, "a95f4075c98e8f0b659d6e38ee9d18f48d5ee6e4de8c797ff2b1f05267f22d3e")
        self.assertEqual({k: len(v) for k, v in values.items()},
                         dict(technologies=467, niveaux_etudes=40, experience=49, type_contrat=25))

    def test_reconstructed_helpers_are_small_explicit_and_separate(self):
        self.assertEqual(reference_overrides.mots_technicien, ["technicien", "BTS", "DUT", "DTS"])
        self.assertEqual(reference_overrides.niveaux_master, ["master", "MBA"])
        self.assertFalse(hasattr(liste, "niveaux_master"))

    def test_production_core_functions_are_unchanged_from_43676ab(self):
        expected = json.loads((FIXTURES / "baseline.json").read_text())
        for source, snapshot in expected.items():
            tree = ast.parse((ROOT / source).read_text(encoding="utf-8-sig"))
            functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
            for name, digest in snapshot["unchanged_function_hashes"].items():
                with self.subTest(source=source, function=name):
                    actual = hashlib.sha256(ast.dump(functions[name], include_attributes=False).encode()).hexdigest()
                    self.assertEqual(actual, digest, "Stage 1 must not silently rewrite the scraper core")

    def test_parser_results_match_original_functions_on_saved_fixtures(self):
        expected = json.loads((FIXTURES / "baseline.json").read_text())
        for source, snapshot in expected.items():
            with self.subTest(source=source):
                ns = load_functions(source)
                actual = canonical_records(ns["collecter_donnees_brutes"](fixture(snapshot["fixture"])))
                self.assertEqual(self._stable_records(actual), self._stable_records(snapshot["records"]))

    def test_both_normalizers_preserve_current_rules(self):
        for source in ("main.py", "indeed.py"):
            normalize = load_functions(source)["Normaliser"]
            with self.subTest(source=source):
                self.assertEqual(normalize("  BAC  +  5 \n PYTHON  "), "bac+5 python")
                self.assertEqual(normalize("ÉCOLE"), "école")
                self.assertEqual(normalize(""), "")

    def test_exact_match_bypasses_fuzzy_threshold(self):
        for source in ("main.py", "indeed.py"):
            matcher = load_functions(source)["extraire_correspondances"]
            self.assertEqual(matcher("Python", ["Python"], seuil=101), ["Python"])

    def test_fuzzy_matching_threshold_and_reference_order(self):
        for source in ("main.py", "indeed.py"):
            matcher = load_functions(source)["extraire_correspondances"]
            self.assertEqual(matcher("pythom", ["Python"], seuil=80), ["Python"])
            self.assertEqual(matcher("pythom", ["Python"], seuil=100), [])
            self.assertEqual(matcher("Docker Python", ["Python", "Docker"]), ["Python", "Docker"])

    def test_short_references_are_not_fuzzy_matched(self):
        for source in ("main.py", "indeed.py"):
            matcher = load_functions(source)["extraire_correspondances"]
            self.assertEqual(matcher("SXL", ["SQL"], seuil=1), [])

    def test_empty_none_and_missing_selector_pages_return_empty_lists(self):
        for source in ("main.py", "indeed.py"):
            parse = load_functions(source)["collecter_donnees_brutes"]
            for html in (None, "", fixture("missing_selectors.html"), fixture("empty_results.html")):
                with self.subTest(source=source, html=html):
                    self.assertEqual(parse(html), [])

    def test_challenge_detector_reports_current_indicators(self):
        for source in ("main.py", "indeed.py"):
            detector = load_functions(source)["detect_security_mechanism"]
            markers = detector(fixture("challenge.html"))
            self.assertTrue({"captcha", "recaptcha", "g-recaptcha", "verify you are human"} <= markers)
            self.assertEqual(detector("<p>Ordinary text</p>"), set())
            self.assertIn("cf-chl-", detector("<script>var challenge='cf-chl-test'</script>"))

    def test_linkedin_master_override_takes_precedence_over_technician(self):
        parse = load_functions("main.py")["collecter_donnees_brutes"]
        result = parse('<li><h3 class="base-search-card__title">Technicien master</h3></li>')
        self.assertEqual(result[0]["niveau"], ["BAC+5-Master"])

    def test_linkedin_technician_override_and_partial_records_are_preserved(self):
        parse = load_functions("main.py")["collecter_donnees_brutes"]
        result = parse('<li><h3 class="base-search-card__title">Technicien</h3></li>')
        self.assertEqual(result[0]["niveau"], ["BAC+2"])
        self.assertEqual(result[0]["Entreprise "], "N/A")
        self.assertEqual(result[0]["Lien "], "N/A")

    def test_indeed_current_parser_uses_substrings_not_the_fuzzy_helper(self):
        ns = load_functions("indeed.py")
        ns["extraire_correspondances"] = lambda *args: self.fail("Indeed does not currently call this helper")
        result = ns["collecter_donnees_brutes"](fixture("indeed_cards.html"))
        self.assertIn("Java", result[0]["Technologie"])
        self.assertIn("JavaScript", result[0]["Technologie"])

    def test_indeed_relative_links_are_expanded_and_absolute_links_retained(self):
        result = load_functions("indeed.py")["collecter_donnees_brutes"](fixture("indeed_cards.html"))
        self.assertEqual(result[0]["Lien "], "https://www.indeed.com/viewjob?jk=fixture123")
        self.assertEqual(result[1]["Lien "], "https://www.indeed.com/viewjob?jk=fixture456")

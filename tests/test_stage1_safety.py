import os
import tempfile
from pathlib import Path

from openpyxl import load_workbook

from tests.legacy_harness import OfflineTestCase, load_functions


class Stage1SafetyTests(OfflineTestCase):
    def test_proxy_lines_keep_current_whitespace_and_blank_line_rules(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "proxies.txt"
            path.write_text(" http://one:1\n\nmalformed\n", encoding="utf-8")
            for source in ("main.py", "indeed.py"):
                self.assertEqual(load_functions(source)["charger_liste_ip"](str(path)),
                                 ["http://one:1", "malformed"])

    def test_excel_export_preserves_the_original_field_mapping_and_hyperlinks(self):
        ns = load_functions("main.py")
        ns["toutes_les_donnees"] = [{"Titre ": "Python", "Entreprise ": "Acme", "Localisation ": "Rabat",
            "Lien ": "https://example.test/job", "Technologie": ["Python", "Docker"], "source ": "fixture",
            "date ": "today", "Contra ": ["CDI"], "niveau": ["master"], "salaire ": "N/A",
            "contacte :": "N/A", "Experienc:": ["3 ans"], "Posting_Date_Status_Detail :": "Activé"}]
        with tempfile.TemporaryDirectory() as folder:
            old = os.getcwd(); os.chdir(folder)
            try:
                ns["Exporter"]()
                workbook = load_workbook("Fichier_Scrapinge_Recrutement.xlsx")
                sheet = workbook["IT Jobs Data"]
                self.assertEqual([cell.value for cell in sheet[1]][:4], ["Company Name", "Job Title", "City / Region", "Job Link"])
                self.assertEqual(sheet["D2"].hyperlink.target, "https://example.test/job")
                self.assertEqual(sheet["F2"].value, "Python, Docker")
            finally:
                os.chdir(old)

    def test_save_before_exit_keeps_current_no_cancel_behavior(self):
        ns = load_functions("main.py")
        ns["toutes_les_donnees"] = [{"Titre ": "unsaved"}]
        ns["messagebox"].askyesnocancel.return_value = False
        with tempfile.TemporaryDirectory() as folder:
            old = os.getcwd(); os.chdir(folder)
            try:
                ns["Onclique"]()
                self.assertTrue(Path("Fichier_sauvergarder_sans_exporter.csv").exists())
                ns["fenetre"].destroy.assert_called_once()
            finally:
                os.chdir(old)


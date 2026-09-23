from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from corporate_scraper.fixture_data import sample_offers
from corporate_scraper.cities import City, MoroccoCityService
from corporate_scraper.models import FilterSpec, JobObservation, RunCounters, RunEvent, RunSpec
from corporate_scraper.runner import RunnerResult
from corporate_scraper.ui import CityPickerDialog, CollectionPage
from corporate_scraper.store import StudyStore
from corporate_scraper.ui import MainWindow


def test_live_startup_shows_saved_results_and_never_demo_rows(qtbot, tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    empty = MainWindow(store=store)
    qtbot.addWidget(empty)
    assert empty.results_page.proxy.rowCount() == 0
    run_id = store.create_run(RunSpec("Saved", ("python",), ("Rabat",), ("linkedin",)))
    store.commit_discovery(run_id, "search:linkedin:python:Rabat:0", [
        JobObservation("linkedin", "saved", "https://example.test/saved", "Saved real offer")
    ])
    restored = MainWindow(store=store)
    qtbot.addWidget(restored)
    assert restored.current_run_id == run_id
    assert restored.results_page.proxy.rowCount() == 1
    assert restored.results_page.export_button.isEnabled()


def test_collection_worker_failure_keeps_saved_results_accessible(qtbot, tmp_path, monkeypatch):
    from threading import Event
    from corporate_scraper.ui import CollectionThread

    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec("Failed", ("python",), ("Rabat",), ("linkedin",))
    run_id = store.create_run(spec)
    store.commit_discovery(run_id, "search:linkedin:python:Rabat:0", [
        JobObservation("linkedin", "saved", "https://example.test/saved", "Saved offer")
    ])
    page = CollectionPage()
    qtbot.addWidget(page)
    page._store, page._run_id = store, run_id
    worker = CollectionThread(store, run_id, spec, Event(), Event())
    def fail():
        raise OSError("Storage unavailable")
    monkeypatch.setattr(worker, "_collect", fail)
    worker.failed.connect(page._collection_failed)
    with qtbot.waitSignal(worker.failed):
        worker.run()
    assert "erreur" in page.state.text()
    assert "Storage unavailable" in page.activity.toPlainText()
    assert not page.pause_button.isEnabled()
    assert page.results_button.isEnabled() and page.export_button.isEnabled()


def test_starting_a_fixture_study_opens_collection(qtbot, tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    window = MainWindow(sample_offers(), store, live_enabled=False)
    qtbot.addWidget(window)
    window.show()

    search = window.search_page
    search.study_name.setText("Étude support Maroc")
    search.terms.setText("support IT")
    start = next(button for button in search.findChildren(QPushButton) if button.text() == "Démarrer l’étude")
    qtbot.mouseClick(start, Qt.LeftButton)

    assert window.pages.currentWidget() is window.collection_page
    assert "Étude support Maroc" not in window.collection_page.state.text()
    assert "objectif: 200 descriptions" in window.collection_page.state.text()
    assert len(store.list_runs()) == 1
    assert "linkedin" in store.run(store.list_runs()[0]["id"])["spec_json"]


def test_results_filter_and_selection_show_evidence(qtbot, tmp_path):
    window = MainWindow(sample_offers(), StudyStore(tmp_path / "studies.db"), live_enabled=False)
    qtbot.addWidget(window)
    window.show()
    window.navigation.setCurrentRow(2)

    results = window.results_page
    results.query.setText("Kubernetes")
    qtbot.waitUntil(lambda: results.proxy.rowCount() == 1)
    assert results.count.text() == "1 offre(s)"
    assert "Kubernetes" in results.summary.text()
    results.table.selectRow(0)
    qtbot.waitUntil(lambda: "Kubernetes" in results.detail.toPlainText())
    assert "Éléments de preuve" in results.detail.toPlainText()
    results.qualification.setCurrentText("excluded")
    qtbot.waitUntil(lambda: results.proxy.rowCount() == 0)


def test_target_mode_explains_listing_count(qtbot, tmp_path):
    window = MainWindow(sample_offers(), StudyStore(tmp_path / "studies.db"), live_enabled=False)
    qtbot.addWidget(window)
    search = window.search_page

    search.target_mode.setCurrentIndex(1)

    assert "Arrête la découverte" in search.target_help.text()


def test_advanced_controls_expand_before_their_values_can_be_changed(qtbot, tmp_path):
    window = MainWindow(sample_offers(), StudyStore(tmp_path / "studies.db"), live_enabled=False)
    qtbot.addWidget(window)
    window.show()

    assert window.search_page.advanced_options.isHidden()
    qtbot.mouseClick(window.search_page.advanced_toggle, Qt.LeftButton)

    assert window.search_page.advanced_options.isVisible()


def test_search_requirements_are_saved_in_the_run_spec(qtbot, tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    window = MainWindow(sample_offers(), store, live_enabled=False)
    qtbot.addWidget(window)
    window.search_page.required_skills.setText("Python, Docker")
    window.search_page.contract_filter.setCurrentText("CDI")
    window.search_page.education_filter.setText("Bac+5")
    window.search_page.include_unknown.setChecked(True)

    window.start_run(window.search_page.run_spec())

    payload = store.run(store.list_runs()[0]["id"])["spec_json"]
    assert '"Python"' in payload and '"Docker"' in payload
    assert '"contract": "CDI"' in payload
    assert '"include_unknown": true' in payload


def test_contact_email_lookup_is_enabled_by_default_and_saved(qtbot, tmp_path):
    window = MainWindow(sample_offers(), StudyStore(tmp_path / "studies.db"), live_enabled=False)
    qtbot.addWidget(window)
    assert window.search_page.find_contact_email.isChecked()

    window.start_run(window.search_page.run_spec())

    payload = window.store.run(window.current_run_id)["spec_json"]
    assert '"find_contact_email": true' in payload


def test_history_opens_persisted_study_in_results(qtbot, tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    run_id = store.create_run(RunSpec("Saved", ("python",), ("Rabat",), ("linkedin",)))
    store.commit_discovery(run_id, "search:linkedin:python:Rabat:0", [
        JobObservation("linkedin", "123", "https://example.test/jobs/123", "Python Engineer", "Acme", "Rabat")
    ])
    window = MainWindow(sample_offers(), store, live_enabled=False)
    qtbot.addWidget(window)

    window.open_run(run_id)

    assert window.pages.currentWidget() is window.results_page
    assert window.results_page.proxy.rowCount() == 1
    assert window.results_page.export_button.isEnabled()


def test_results_sidebar_loads_the_active_persisted_study(qtbot, tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    run_id = store.create_run(RunSpec("Sidebar", ("python",), ("Rabat",), ("linkedin",)))
    store.commit_discovery(run_id, "search:linkedin:python:Rabat:0", [
        JobObservation("linkedin", "123", "https://example.test/jobs/123", "Python Engineer", "Acme", "Rabat")
    ])
    window = MainWindow(sample_offers(), store, live_enabled=False)
    qtbot.addWidget(window)
    window.current_run_id = run_id

    window.navigation.setCurrentRow(2)

    assert window.results_page.proxy.rowCount() == 1
    assert "Python Engineer" in window.results_page.detail.toPlainText()


def test_collection_completion_displays_persisted_counters(qtbot, tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec("Counters", ("python",), ("Rabat",), ("linkedin",), target=1)
    run_id = store.create_run(spec)
    store.commit_discovery(run_id, "search:linkedin:python:Rabat:0", [
        JobObservation("linkedin", "one", "https://example.test/one", "Python Engineer")
    ])
    store.commit_detail(run_id, "one", "Python required", "available", "extracted", ())
    page = CollectionPage(); qtbot.addWidget(page)
    page._store, page._run_id, page._run_spec = store, run_id, spec

    page._completed(RunnerResult("target_reached", 2, ("saved",)))

    assert page.metrics["found"].text() == "1"
    assert page.metrics["details"].text() == "1"
    assert "tentatives: 2" in page.state.text()


def test_collection_completion_explains_filters_that_exclude_retrieved_descriptions(qtbot, tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec("Filtered", ("python",), ("Rabat",), ("linkedin",), target=1,
                   filters=FilterSpec(contract="Alternance"))
    run_id = store.create_run(spec)
    store.commit_discovery(run_id, "search:linkedin:python:Rabat:0", [
        JobObservation("linkedin", "one", "https://example.test/one", "Python Engineer")
    ])
    store.commit_detail(run_id, "one", "Python required", "available", "extracted", (), "unknown")
    page = CollectionPage(); qtbot.addWidget(page)
    page._store, page._run_id, page._run_spec = store, run_id, spec

    page._completed(RunnerResult("results_exhausted", 2, ("saved",)))

    assert page.metrics["details"].text() == "1"
    assert "Alternance" in page.state.text()
    assert page.results_button.isEnabled() and page.export_button.isEnabled()


def test_collection_progress_event_updates_stage_bar_and_committed_counts(qtbot):
    page = CollectionPage(); qtbot.addWidget(page)
    page._run_spec = RunSpec("Progress", ("python",), ("Rabat",), ("linkedin",), target=4)

    page._on_progress(RunEvent("qualifying", "linkedin", "description saved", 7,
                               RunCounters(found=8, unique=5, descriptions=3, matching_target=3, duplicates=1, incomplete=1)))

    assert page.progress.value() == 75
    assert page.metrics["unique"].text() == "5"
    assert page.stage_cards["qualifying"][1].text() == "Extraction des besoins"
    assert "tentatives: 7" in page.state.text()


def test_city_picker_uses_cached_multiselect_cities(qtbot, tmp_path):
    service = MoroccoCityService(tmp_path / "cities.json")
    service._write_cache([City("Casablanca"), City("Rabat"), City("Tanger")])
    dialog = CityPickerDialog(service, {"Rabat"})
    qtbot.addWidget(dialog)

    assert dialog.cities.count() == 3
    dialog.search.setText("tan")
    dialog._select_visible()

    assert dialog.selected_names() == ["Rabat", "Tanger"]

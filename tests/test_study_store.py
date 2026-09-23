from corporate_scraper.models import FieldEvidence, JobObservation, RunSpec, TargetMode
from corporate_scraper.store import StudyStore


def spec() -> RunSpec:
    return RunSpec(name="Étude Maroc", queries=("python",), cities=("Rabat",), sources=("linkedin",))


def offer(key: str = "job-1") -> JobObservation:
    return JobObservation(source="linkedin", source_key=key, canonical_url=f"https://example.test/{key}",
                          title="Développeur Python", company="Acme", location="Rabat", skills=("Python",))


def test_discovery_is_idempotent_and_persists_across_reopen(tmp_path):
    path = tmp_path / "studies.db"
    store = StudyStore(path)
    run_id = store.create_run(spec())

    assert store.commit_discovery(run_id, "search:linkedin:rabat:0", [offer(), offer()]) == (1, 1)
    assert store.commit_discovery(run_id, "search:linkedin:rabat:0", [offer()]) == (0, 0)

    reopened = StudyStore(path)
    rows = reopened.offers(run_id)
    assert len(rows) == 1
    assert rows[0]["title"] == "Développeur Python"
    assert reopened.incomplete_detail_keys(run_id) == ["job-1"]


def test_detail_and_evidence_commit_together(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    run_id = store.create_run(spec())
    store.commit_discovery(run_id, "search:linkedin:rabat:0", [offer()])

    evidence = (FieldEvidence("skill_required", "Python", "Python requis", "exact", 100.0),)
    store.commit_detail(run_id, "job-1", "Python requis pour ce poste.", "available", "verified", evidence)

    row = store.offers(run_id)[0]
    assert row["description"] == "Python requis pour ce poste."
    assert row["description_status"] == "available"
    assert store.incomplete_detail_keys(run_id) == []
    saved_evidence = store.evidence_for_offer(row["id"])
    assert [(item["value"], item["method"]) for item in saved_evidence] == [("Python", "exact")]
    counts = store.counters(run_id, TargetMode.DESCRIPTIONS)
    assert (counts.unique, counts.descriptions, counts.matching_target, counts.incomplete) == (1, 1, 1, 0)


def test_run_spec_rejects_unsafe_limits():
    try:
        RunSpec(name="", queries=("python",), cities=("Rabat",), sources=("linkedin",))
    except ValueError as error:
        assert "name" in str(error).lower()
    else:
        raise AssertionError("An empty name must be rejected")


def test_listing_target_preserves_overflow_without_counting_it(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    run_id = store.create_run(spec())
    store.commit_discovery(run_id, "search:1", [offer("one"), offer("two"), offer("three")], max_selected=2)

    assert [row["source_key"] for row in store.offers(run_id)] == ["one", "two"]
    assert [row["source_key"] for row in store.offers(run_id, include_overflow=True)] == ["one", "two", "three"]
    counters = store.counters(run_id, TargetMode.LISTINGS)
    assert (counters.found, counters.unique, counters.matching_target) == (3, 2, 2)


def test_public_contact_outcome_is_persisted(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    run_id = store.create_run(spec())
    store.commit_discovery(run_id, "search:1", [offer()])

    store.commit_contact(run_id, "job-1", status="found", email="jobs@acme.ma", level="job_post",
                         url="https://example.test/job-1", confidence=100, source="linkedin")

    row = store.offers(run_id)[0]
    assert (row["contact_email"], row["contact_status"], row["contact_level"], row["contact_confidence"]) == ("jobs@acme.ma", "found", "job_post", 100)

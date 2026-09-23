from corporate_scraper.models import FetchOutcome, FetchOutcomeKind, FilterSpec, JobObservation, RunSpec, TargetMode
from corporate_scraper.runner import CollectionRunner
from corporate_scraper.sources import SourceAdapter
from corporate_scraper.store import StudyStore
from corporate_scraper.transport import TransportResult


class Adapter(SourceAdapter):
    source = "fixture"
    base_url = "https://fixture.test"
    def search_url(self, query, location, start): return f"search:{start}"
    def _cards(self, soup): return []
    def parse_search(self, html):
        return [JobObservation("fixture", key, f"https://fixture.test/{key}", f"Role {key}") for key in html.split(",") if key]
    def parse_description(self, html): return html


class ContactAdapter(Adapter):
    def public_contact_pages(self, html, job_url):
        if job_url.endswith("/company"):
            return (("company_contact_page", "https://acme.example/contact"),)
        return (("recruiter_linkedin_profile", "https://fixture.test/poster"), ("company_linkedin_profile", "https://fixture.test/company"))


class Transport:
    def __init__(self, responses): self.responses = responses; self.urls = []
    def fetch(self, adapter, url):
        self.urls.append(url)
        return self.responses[url]


def response(html):
    return TransportResult(FetchOutcome(FetchOutcomeKind.SUCCESS), html=html, status_code=200)


def test_description_target_stops_after_persisting_required_details(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Descriptions", queries=("python",), cities=("Rabat",), sources=("fixture",), target=2, max_pages=2)
    run_id = store.create_run(spec)
    transport = Transport({"search:0": response("one,two"), "https://fixture.test/one": response("Python required"),
                           "https://fixture.test/two": response("Docker required")})

    result = CollectionRunner(store, {"fixture": Adapter()}, {"fixture": transport}).run(run_id, spec)

    assert result.state == "target_reached"
    assert result.attempts == 3
    assert store.counters(run_id, TargetMode.DESCRIPTIONS).matching_target == 2


def test_listing_target_preserves_overflow_and_stops_discovery(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Listings", queries=("python",), cities=("Rabat",), sources=("fixture",), target=1,
                   target_mode=TargetMode.LISTINGS, max_pages=2)
    run_id = store.create_run(spec)
    transport = Transport({"search:0": response("one,two"), "https://fixture.test/one": response("Description")})

    result = CollectionRunner(store, {"fixture": Adapter()}, {"fixture": transport}).run(run_id, spec)

    assert result.state == "target_reached"
    assert [row["source_key"] for row in store.offers(run_id)] == ["one"]
    assert [row["source_key"] for row in store.offers(run_id, include_overflow=True)] == ["one", "two"]
    assert "search:25" not in transport.urls


def test_resume_does_not_refetch_a_checkpointed_search_page(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Resume", queries=("python",), cities=("Rabat",), sources=("fixture",), target=2, max_pages=1)
    run_id = store.create_run(spec)
    store.commit_discovery(run_id, "search:fixture:python:Rabat:0", [
        JobObservation("fixture", "one", "https://fixture.test/one", "Role one")
    ])
    transport = Transport({"https://fixture.test/one": response("Description")})

    result = CollectionRunner(store, {"fixture": Adapter()}, {"fixture": transport}).run(run_id, spec)

    assert result.state == "results_exhausted"
    assert transport.urls == ["https://fixture.test/one"]
    assert any("already checkpointed" in message for message in result.messages)


def test_transient_detail_failure_is_left_pending_for_a_resume(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Retry", queries=("python",), cities=("Rabat",), sources=("fixture",), target=2, max_pages=1)
    run_id = store.create_run(spec)
    transport = Transport({
        "search:0": response("one"),
        "https://fixture.test/one": TransportResult(FetchOutcome(FetchOutcomeKind.TRANSPORT_ERROR), None, None),
    })

    result = CollectionRunner(store, {"fixture": Adapter()}, {"fixture": transport}).run(run_id, spec)

    assert result.state == "results_exhausted"
    assert store.incomplete_detail_keys(run_id) == ["one"]
    assert any("pending resume" in message for message in result.messages)


def test_description_target_excludes_unknown_required_filters_by_default(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Filtered", queries=("python",), cities=("Rabat",), sources=("fixture",), target=1,
                   max_pages=1, filters=FilterSpec(education="Bac+5"))
    run_id = store.create_run(spec)
    transport = Transport({"search:0": response("one"), "https://fixture.test/one": response("Python required")})

    result = CollectionRunner(store, {"fixture": Adapter()}, {"fixture": transport}).run(run_id, spec)

    assert result.state == "results_exhausted"
    counters = store.counters(run_id)
    assert (counters.descriptions, counters.matching_target) == (1, 0)
    assert store.qualification_counts(run_id) == {"unknown": 1}


def test_repeated_search_page_stops_later_requests_for_that_search(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Repeated", queries=("python",), cities=("Rabat",), sources=("fixture",), target=5, max_pages=3)
    run_id = store.create_run(spec)
    transport = Transport({
        "search:0": response("one"), "search:25": response("one"),
        "https://fixture.test/one": response("Description"),
    })

    result = CollectionRunner(store, {"fixture": Adapter()}, {"fixture": transport}).run(run_id, spec)

    assert result.state == "results_exhausted"
    assert "search:50" not in transport.urls
    assert any("repeated page" in message for message in result.messages)


def test_pacing_wait_can_be_cancelled_before_the_next_request(tmp_path):
    from threading import Event

    store = StudyStore(tmp_path / "studies.db")
    runner = CollectionRunner(store, {"fixture": Adapter()}, {"fixture": Transport({})}, min_request_interval_seconds=10)
    runner._last_request["fixture"] = __import__("time").monotonic()
    stopped = Event(); stopped.set()

    assert runner._wait_to_dispatch("fixture", stopped, None) is False


def test_runner_emits_committed_progress_for_discovery_and_description(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Events", queries=("python",), cities=("Rabat",), sources=("fixture",), target=1, max_pages=1)
    run_id = store.create_run(spec)
    events = []
    transport = Transport({"search:0": response("one"), "https://fixture.test/one": response("Python required")})

    CollectionRunner(store, {"fixture": Adapter()}, {"fixture": transport}, event_callback=events.append).run(run_id, spec)

    assert [event.stage for event in events] == ["preparing", "discovering", "discovering", "describing", "qualifying", "contact", "complete"]
    assert events[-1].counters.matching_target == 1


def test_contact_lookup_prefers_a_visible_email_in_the_job_post(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Contact", queries=("python",), cities=("Rabat",), sources=("fixture",), target=1, max_pages=1)
    run_id = store.create_run(spec)
    transport = Transport({"search:0": response("one"), "https://fixture.test/one": response("Apply at jobs@acme.ma")})

    CollectionRunner(store, {"fixture": ContactAdapter()}, {"fixture": transport}).run(run_id, spec)

    row = store.offers(run_id)[0]
    assert (row["contact_email"], row["contact_level"], row["contact_status"], row["contact_confidence"]) == ("jobs@acme.ma", "job_post", "found", 100)
    assert transport.urls == ["search:0", "https://fixture.test/one"]


def test_contact_lookup_uses_explicit_public_pages_then_records_not_found(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Contact pages", queries=("python",), cities=("Rabat",), sources=("fixture",), target=1, max_pages=1)
    run_id = store.create_run(spec)
    transport = Transport({"search:0": response("one"), "https://fixture.test/one": response("No email"),
                           "https://fixture.test/poster": response("Contact recruiter@acme.ma"),
                           "https://fixture.test/company": response("No email"),
                           "https://acme.example/contact": response("company@acme.ma")})

    CollectionRunner(store, {"fixture": ContactAdapter()}, {"fixture": transport}).run(run_id, spec)

    row = store.offers(run_id)[0]
    assert (row["contact_email"], row["contact_level"], row["contact_confidence"]) == ("recruiter@acme.ma", "recruiter_linkedin_profile", 88)
    assert "https://acme.example/contact" not in transport.urls


def test_contact_lookup_reaches_company_contact_page_after_public_profiles(tmp_path):
    store = StudyStore(tmp_path / "studies.db")
    spec = RunSpec(name="Deep contact", queries=("python",), cities=("Rabat",), sources=("fixture",), target=1, max_pages=1)
    run_id = store.create_run(spec)
    transport = Transport({"search:0": response("one"), "https://fixture.test/one": response("No email"),
                           "https://fixture.test/poster": response("No email"), "https://fixture.test/company": response("No email"),
                           "https://acme.example/contact": response("Write to hiring@acme.example")})

    CollectionRunner(store, {"fixture": ContactAdapter()}, {"fixture": transport}).run(run_id, spec)

    row = store.offers(run_id)[0]
    # Contact page is 90%; matching its official page domain earns the 7-point boost.
    assert (row["contact_email"], row["contact_level"], row["contact_confidence"]) == ("hiring@acme.example", "company_contact_page", 97)

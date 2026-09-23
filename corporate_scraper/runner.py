"""Budgeted, resumable collection coordination shared by desktop and CLI callers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import product
import json
from threading import Event
from time import monotonic
from collections.abc import Callable
from typing import Mapping

from .extraction import ReferenceTerm, evaluate_filters, extract_structured_requirements
from .contacts import public_email
from .locking import RunLock
from .models import FetchOutcomeKind, RunEvent, RunSpec, TargetMode
from .sources import SourceAdapter
from .store import StudyStore
from .transport import HttpTransport, TransportResult


LEGACY_PAGE_STEP = 25


@dataclass(frozen=True, slots=True)
class RunnerResult:
    state: str
    attempts: int
    messages: tuple[str, ...]


class CollectionRunner:
    """Coordinates sources without importing Qt or sharing worker-owned sessions."""

    def __init__(self, store: StudyStore, adapters: Mapping[str, SourceAdapter], transports: Mapping[str, HttpTransport],
                 references: tuple[ReferenceTerm, ...] = (), min_request_interval_seconds: float = 0.0,
                 event_callback: Callable[[RunEvent], None] | None = None) -> None:
        self.store = store
        self.adapters = dict(adapters)
        self.transports = dict(transports)
        self.references = references
        self.min_request_interval_seconds = max(0.0, min_request_interval_seconds)
        self.event_callback = event_callback
        self._last_request: dict[str, float] = {}

    def run(self, run_id: str, spec: RunSpec, stop_event: Event | None = None,
            pause_event: Event | None = None) -> RunnerResult:
        """Run one collection with exclusive ownership of the study directory."""
        lock = RunLock(self.store.path.parent)
        try:
            lock.acquire()
        except RuntimeError as error:
            return RunnerResult("run_locked", 0, (str(error),))
        try:
            return self._run_locked(run_id, spec, stop_event, pause_event)
        finally:
            lock.release()

    def _run_locked(self, run_id: str, spec: RunSpec, stop_event: Event | None = None,
                    pause_event: Event | None = None) -> RunnerResult:
        stopper = stop_event or Event()
        attempts = 0
        messages: list[str] = []
        blocked_sources: set[str] = set()
        exhausted_searches: set[tuple[str, str, str]] = set()
        page_signatures: dict[tuple[str, str, str], tuple[str, ...]] = {}
        deadline = datetime.now(UTC) + timedelta(minutes=spec.max_duration_minutes)
        self.store.set_run_state(run_id, "running")
        self._emit(run_id, spec, "preparing", None, "Étude enregistrée : préparation des sources.", attempts)
        # Resume any persisted details before issuing another search request.
        attempts, state = self._collect_pending_details(run_id, spec, stopper, attempts, messages, deadline, pause_event)
        if state:
            return self._finish(run_id, state, attempts, messages)
        work = tuple(product(range(spec.max_pages), spec.sources, spec.queries, spec.cities))
        for page_index, source, query, city in work:
            state = self._terminal_state(run_id, spec, stopper, attempts, deadline, pause_event)
            if state:
                return self._finish(run_id, state, attempts, messages)
            if source in blocked_sources:
                continue
            search_scope = (source, query, city)
            if search_scope in exhausted_searches:
                continue
            adapter = self.adapters.get(source)
            transport = self.transports.get(source)
            if adapter is None or transport is None:
                blocked_sources.add(source)
                messages.append(f"{source}: adapter or transport unavailable")
                self._emit(run_id, spec, "source_unavailable", source, messages[-1], attempts)
                continue
            task_key = f"search:{source}:{query}:{city}:{page_index}"
            if self.store.task_complete(run_id, task_key):
                messages.append(f"{source}: page {page_index + 1} already checkpointed")
                self._emit(run_id, spec, "discovering", source, messages[-1], attempts)
                continue
            if not self._wait_to_dispatch(source, stopper, pause_event):
                return self._finish(run_id, "stopped", attempts, messages)
            self._emit(run_id, spec, "discovering", source,
                       f"{source.title()} : recherche {page_index + 1}/{spec.max_pages} pour {city}.", attempts)
            response = transport.fetch(adapter, adapter.search_url(query, city, page_index * LEGACY_PAGE_STEP))
            self._last_request[source] = monotonic()
            attempts += 1
            if response.outcome.kind is FetchOutcomeKind.SUCCESS:
                maximum = spec.target if spec.target_mode is TargetMode.LISTINGS else None
                observations = adapter.parse_search(response.html or "")
                signature = tuple(observation.source_key for observation in observations)
                if not signature:
                    exhausted_searches.add(search_scope)
                    messages.append(f"{source}: no parsable offers for {city}; search exhausted")
                    self._emit(run_id, spec, "discovering", source, messages[-1], attempts)
                    continue
                if page_signatures.get(search_scope) == signature:
                    exhausted_searches.add(search_scope)
                    messages.append(f"{source}: repeated page for {city}; search exhausted")
                    self._emit(run_id, spec, "discovering", source, messages[-1], attempts)
                    continue
                page_signatures[search_scope] = signature
                added, duplicates = self.store.commit_discovery(run_id, task_key, observations, maximum)
                messages.append(f"{source}: page {page_index + 1}, {added} added, {duplicates} duplicates")
                self._emit(run_id, spec, "discovering", source, messages[-1], attempts)
                attempts, state = self._collect_pending_details(run_id, spec, stopper, attempts, messages, deadline, pause_event)
                if state:
                    return self._finish(run_id, state, attempts, messages)
            elif response.outcome.kind in (FetchOutcomeKind.BLOCKED, FetchOutcomeKind.THROTTLED):
                blocked_sources.add(source)
                messages.append(f"{source}: {response.outcome.kind.value}; source paused")
                self._emit(run_id, spec, "source_unavailable", source, messages[-1], attempts)
            elif response.outcome.kind is FetchOutcomeKind.EMPTY:
                exhausted_searches.add(search_scope)
                messages.append(f"{source}: no results for {city}")
                self._emit(run_id, spec, "discovering", source, messages[-1], attempts)
            else:
                messages.append(f"{source}: {response.outcome.kind.value}")
                self._emit(run_id, spec, "discovering", source, messages[-1], attempts)
        state = self._terminal_state(run_id, spec, stopper, attempts, deadline, pause_event) or "results_exhausted"
        return self._finish(run_id, state, attempts, messages)

    def _collect_pending_details(self, run_id: str, spec: RunSpec, stopper: Event, attempts: int,
                                 messages: list[str], deadline: datetime, pause_event: Event | None) -> tuple[int, str | None]:
        for offer in self.store.pending_detail_offers(run_id):
            state = self._detail_terminal_state(run_id, spec, stopper, attempts, deadline, pause_event)
            if state:
                return attempts, state
            adapter = self.adapters[offer["source"]]
            transport = self.transports[offer["source"]]
            result: TransportResult | None = None
            fetch_detail = getattr(transport, "fetch_detail", transport.fetch)
            # A transient transport/server error receives at most two retries;
            # every attempt is visible to the global request budget.
            for _ in range(3):
                if not self._wait_to_dispatch(offer["source"], stopper, pause_event):
                    return attempts, "stopped"
                self._emit(run_id, spec, "describing", offer["source"],
                           f"{offer['source'].title()} : lecture de la description « {offer['title']} ».", attempts)
                result = fetch_detail(adapter, offer["canonical_url"])
                self._last_request[offer["source"]] = monotonic()
                attempts += 1
                if result.outcome.kind is not FetchOutcomeKind.TRANSPORT_ERROR:
                    break
                if attempts >= spec.max_attempts:
                    return attempts, "budget_reached"
            assert result is not None
            if result.outcome.kind is FetchOutcomeKind.SUCCESS:
                description = adapter.parse_description(result.html or "")
                if description:
                    evidence = extract_structured_requirements(description, self.references)
                    qualification = evaluate_filters(evidence, spec.filters)
                    self.store.commit_detail(run_id, offer["source_key"], description, "available", "extracted", evidence, qualification, source=offer["source"])
                    messages.append(f"{offer['source']}: description saved for {offer['source_key']}")
                    self._emit(run_id, spec, "qualifying", offer["source"], messages[-1], attempts)
                else:
                    self.store.commit_detail(run_id, offer["source_key"], "", "unavailable", "incomplete", (), evaluate_filters((), spec.filters), source=offer["source"])
                    messages.append(f"{offer['source']}: description unavailable for {offer['source_key']}")
                    self._emit(run_id, spec, "describing", offer["source"], messages[-1], attempts)
                if spec.find_contact_email:
                    attempts, contact_state, contact_message = self._collect_public_contact(
                        run_id, spec, offer, adapter, transport, result.html or "", description or "", stopper,
                        attempts, deadline, pause_event,
                    )
                    messages.append(contact_message)
                    self._emit(run_id, spec, "contact", offer["source"], contact_message, attempts)
                    if contact_state:
                        return attempts, contact_state
            elif result.outcome.kind is FetchOutcomeKind.TRANSPORT_ERROR:
                # There is no source fact to persist yet. Leaving the offer
                # pending makes a later resume retry it with its original URL.
                messages.append(f"{offer['source']}: transient detail failure for {offer['source_key']}; pending resume")
                self._emit(run_id, spec, "describing", offer["source"], messages[-1], attempts)
            else:
                self.store.commit_detail(run_id, offer["source_key"], "", "unavailable", "incomplete", (), evaluate_filters((), spec.filters), source=offer["source"])
                messages.append(f"{offer['source']}: detail {result.outcome.kind.value} for {offer['source_key']}")
                self._emit(run_id, spec, "describing", offer["source"], messages[-1], attempts)
        return attempts, None

    def _collect_public_contact(self, run_id: str, spec: RunSpec, offer, adapter: SourceAdapter,
                                transport: HttpTransport, detail_html: str, description: str, stopper: Event,
                                attempts: int, deadline: datetime, pause_event: Event | None) -> tuple[int, str | None, str]:
        """Check visible post text, then explicitly linked public pages only."""
        direct = public_email(description or detail_html, "job_post", offer["canonical_url"])
        if direct:
            self.store.commit_contact(run_id, offer["source_key"], status="found", email=direct.email,
                                      level=direct.level, url=direct.url, confidence=direct.confidence, source=offer["source"])
            return attempts, None, f"{offer['source']}: public email found in job post"
        pages = list(adapter.public_contact_pages(detail_html, offer["canonical_url"]))
        visited = {offer["canonical_url"]}
        checked_pages = 0
        while pages and checked_pages < 4:
            level, url = pages.pop(0)
            if url in visited:
                continue
            visited.add(url)
            state = self._contact_terminal_state(spec, stopper, attempts, deadline, pause_event)
            if state:
                self.store.commit_contact(run_id, offer["source_key"], status="unavailable", source=offer["source"])
                return attempts, state, f"{offer['source']}: public email check incomplete"
            if not self._wait_to_dispatch(offer["source"], stopper, pause_event):
                self.store.commit_contact(run_id, offer["source_key"], status="unavailable", source=offer["source"])
                return attempts, "stopped", f"{offer['source']}: public email check stopped"
            fetch_detail = getattr(transport, "fetch_detail", transport.fetch)
            response = fetch_detail(adapter, url)
            self._last_request[offer["source"]] = monotonic()
            attempts += 1
            checked_pages += 1
            if response.outcome.kind is not FetchOutcomeKind.SUCCESS or not response.html:
                continue
            found = public_email(response.html, level, url)
            if found:
                self.store.commit_contact(run_id, offer["source_key"], status="found", email=found.email,
                                          level=found.level, url=found.url, confidence=found.confidence, source=offer["source"])
                return attempts, None, f"{offer['source']}: public email found via {level}"
            for next_level, next_url in adapter.public_contact_pages(response.html, url):
                if next_url not in visited and all(known_url != next_url for _, known_url in pages):
                    pages.append((next_level, next_url))
        self.store.commit_contact(run_id, offer["source_key"], status="not_found", source=offer["source"])
        return attempts, None, f"{offer['source']}: no public contact email found"

    @staticmethod
    def _contact_terminal_state(spec: RunSpec, stopper: Event, attempts: int, deadline: datetime,
                                pause_event: Event | None) -> str | None:
        while pause_event and pause_event.is_set():
            if stopper.wait(0.1):
                return "stopped"
        if stopper.is_set():
            return "stopped"
        if attempts >= spec.max_attempts:
            return "budget_reached"
        if datetime.now(UTC) >= deadline:
            return "duration_reached"
        return None

    def _terminal_state(self, run_id: str, spec: RunSpec, stopper: Event, attempts: int,
                        deadline: datetime, pause_event: Event | None = None) -> str | None:
        while pause_event and pause_event.is_set():
            if stopper.wait(0.1):
                return "stopped"
        if stopper.is_set():
            return "stopped"
        if attempts >= spec.max_attempts:
            return "budget_reached"
        if datetime.now(UTC) >= deadline:
            return "duration_reached"
        counters = self.store.counters(run_id, spec.target_mode)
        if counters.matching_target >= spec.target:
            return "target_reached"
        return None

    def _detail_terminal_state(self, run_id: str, spec: RunSpec, stopper: Event, attempts: int,
                               deadline: datetime, pause_event: Event | None = None) -> str | None:
        while pause_event and pause_event.is_set():
            if stopper.wait(0.1):
                return "stopped"
        if stopper.is_set():
            return "stopped"
        if attempts >= spec.max_attempts:
            return "budget_reached"
        if datetime.now(UTC) >= deadline:
            return "duration_reached"
        # Listing mode reaches its discovery target before enrichment begins;
        # its selected offers still deserve their budgeted detail collection.
        if spec.target_mode is TargetMode.DESCRIPTIONS:
            counters = self.store.counters(run_id, spec.target_mode)
            if counters.matching_target >= spec.target:
                return "target_reached"
        return None

    def _finish(self, run_id: str, state: str, attempts: int, messages: list[str]) -> RunnerResult:
        self.store.set_run_state(run_id, state)
        # This follows the state commit, so callers never present a completed
        # stage before its data is durable.
        spec = RunSpec.from_dict(json.loads(self.store.run(run_id)["spec_json"]))
        self._emit(run_id, spec, "complete", None, f"Collecte terminée : {state.replace('_', ' ')}.", attempts)
        return RunnerResult(state, attempts, tuple(messages))

    def _emit(self, run_id: str, spec: RunSpec, stage: str, source: str | None, message: str, attempts: int) -> None:
        if self.event_callback is None:
            return
        self.event_callback(RunEvent(stage, source, message, attempts, self.store.counters(run_id, spec.target_mode)))

    def _wait_to_dispatch(self, source: str, stopper: Event, pause_event: Event | None) -> bool:
        """Apply restrained source pacing with cancellation checked every 250 ms."""
        previous = self._last_request.get(source)
        if previous is None:
            return not stopper.is_set()
        remaining = self.min_request_interval_seconds - (monotonic() - previous)
        while remaining > 0:
            if stopper.wait(min(0.25, remaining)):
                return False
            while pause_event and pause_event.is_set():
                if stopper.wait(0.1):
                    return False
            remaining = self.min_request_interval_seconds - (monotonic() - previous)
        return True

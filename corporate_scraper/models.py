"""Shared, UI-independent contracts for collection and persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class TargetMode(StrEnum):
    DESCRIPTIONS = "descriptions"
    LISTINGS = "listings"


class FetchOutcomeKind(StrEnum):
    SUCCESS = "success"
    EMPTY = "empty"
    RENDERING_NEEDED = "rendering_needed"
    BLOCKED = "blocked"
    THROTTLED = "throttled"
    TRANSPORT_ERROR = "transport_error"
    LAYOUT_ERROR = "layout_error"


class TaskKind(StrEnum):
    SEARCH = "search"
    DETAIL = "detail"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class FilterSpec:
    skills: tuple[str, ...] = ()
    contract: str | None = None
    education: str | None = None
    experience: str | None = None
    include_unknown: bool = False


@dataclass(frozen=True, slots=True)
class RunSpec:
    name: str
    queries: tuple[str, ...]
    cities: tuple[str, ...]
    sources: tuple[str, ...]
    target: int = 200
    target_mode: TargetMode = TargetMode.DESCRIPTIONS
    max_pages: int = 20
    max_attempts: int = 1_000
    max_duration_minutes: int = 120
    balanced: bool = True
    find_contact_email: bool = True
    filters: FilterSpec = field(default_factory=FilterSpec)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("A study name is required.")
        if not self.queries or not all(query.strip() for query in self.queries):
            raise ValueError("At least one non-empty query is required.")
        if not self.cities or not all(city.strip() for city in self.cities):
            raise ValueError("At least one city is required.")
        if not self.sources or not all(source.strip() for source in self.sources):
            raise ValueError("At least one source is required.")
        if not 1 <= self.target <= 10_000:
            raise ValueError("The target must be between 1 and 10,000.")
        if not 1 <= self.max_pages <= 100:
            raise ValueError("The page limit must be between 1 and 100.")
        if not 1 <= self.max_attempts <= 10_000:
            raise ValueError("The attempt limit must be between 1 and 10,000.")
        if not 1 <= self.max_duration_minutes <= 12 * 60:
            raise ValueError("The duration limit must be between 1 minute and 12 hours.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunSpec":
        values = dict(payload)
        values["queries"] = tuple(values["queries"])
        values["cities"] = tuple(values["cities"])
        values["sources"] = tuple(values["sources"])
        values["target_mode"] = TargetMode(values.get("target_mode", TargetMode.DESCRIPTIONS))
        values["filters"] = FilterSpec(**values.get("filters", {}))
        return cls(**values)


@dataclass(frozen=True, slots=True)
class FieldEvidence:
    field: str
    value: str
    excerpt: str
    method: str
    score: float | None = None
    rule_version: str = "v1"


@dataclass(frozen=True, slots=True)
class JobObservation:
    source: str
    source_key: str
    canonical_url: str
    title: str
    company: str | None = None
    location: str | None = None
    posted_text: str | None = None
    skills: tuple[str, ...] = ()
    experience: str | None = None
    contract: str | None = None
    description: str | None = None
    description_status: str = "pending"
    quality: str = "unreviewed"
    evidence: tuple[FieldEvidence, ...] = ()

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.source_key.strip():
            raise ValueError("A source and stable source key are required.")
        if not self.canonical_url.strip() or not self.title.strip():
            raise ValueError("A canonical URL and title are required.")


@dataclass(frozen=True, slots=True)
class FetchOutcome:
    kind: FetchOutcomeKind
    message: str = ""
    retry_after_seconds: int | None = None
    transport: str = "http"


@dataclass(frozen=True, slots=True)
class RunCounters:
    found: int
    unique: int
    descriptions: int
    matching_target: int
    duplicates: int
    incomplete: int


@dataclass(frozen=True, slots=True)
class RunEvent:
    """A committed collection update suitable for a UI or CLI status view.

    Events deliberately contain only durable counters and a human-readable
    message.  The collection engine stays independent from Qt while callers
    can render an honest, live view of the current stage.
    """

    stage: str
    source: str | None
    message: str
    attempts: int
    counters: RunCounters

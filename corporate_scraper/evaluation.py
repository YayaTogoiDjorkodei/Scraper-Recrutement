"""Transparent precision/recall reporting for a human-labelled corpus."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .models import FieldEvidence


@dataclass(frozen=True, slots=True)
class FieldMetrics:
    field: str
    expected: int
    predicted: int
    true_positive: int

    @property
    def precision(self) -> float:
        return self.true_positive / self.predicted if self.predicted else 1.0

    @property
    def recall(self) -> float:
        return self.true_positive / self.expected if self.expected else 1.0


def evaluate(expected: Iterable[FieldEvidence], predicted: Iterable[FieldEvidence]) -> tuple[FieldMetrics, ...]:
    """Compare field/value labels; excerpts and matching method stay review data."""
    expected_keys = {(item.field, item.value.casefold()) for item in expected}
    predicted_keys = {(item.field, item.value.casefold()) for item in predicted}
    fields = defaultdict(lambda: [0, 0, 0])
    for field, _ in expected_keys:
        fields[field][0] += 1
    for field, _ in predicted_keys:
        fields[field][1] += 1
    for field, _ in expected_keys & predicted_keys:
        fields[field][2] += 1
    return tuple(FieldMetrics(field, *counts) for field, counts in sorted(fields.items()))

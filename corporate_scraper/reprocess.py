"""Re-extract saved descriptions without performing any network request."""
import json

from .extraction import evaluate_filters, extract_structured_requirements
from .locking import RunLock
from .models import RunSpec
from .references import TECHNOLOGY_REFERENCES
from .text import description_text


def reprocess_study(store, run_id: str) -> int:
    lock = RunLock(store.path.parent)
    lock.acquire()
    try:
        spec = RunSpec.from_dict(json.loads(store.run(run_id)["spec_json"]))
        processed = 0
        for offer in store.offers(run_id, include_overflow=True):
            raw = offer["raw_description"] or offer["description"]
            if not raw:
                with store._connection() as connection:
                    connection.execute("UPDATE offers SET qualification_status=? WHERE id=?",
                                       (evaluate_filters((), spec.filters), offer["id"]))
                continue
            text = description_text(raw)
            evidence = extract_structured_requirements(text, TECHNOLOGY_REFERENCES)
            store.commit_detail(run_id, offer["source_key"], raw, "available" if text else "unavailable",
                                "extracted" if text else "incomplete", evidence,
                                evaluate_filters(evidence, spec.filters), source=offer["source"])
            processed += 1
        return processed
    finally:
        lock.release()

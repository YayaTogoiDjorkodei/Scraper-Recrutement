from corporate_scraper.models import FilterSpec, RunSpec, TargetMode


def test_run_spec_round_trip_preserves_typed_values():
    original = RunSpec("Round trip", ("python",), ("Rabat",), ("linkedin",), target_mode=TargetMode.LISTINGS,
                       filters=FilterSpec(skills=("Python",), include_unknown=True))

    restored = RunSpec.from_dict(original.to_dict())

    assert restored == original

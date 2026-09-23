from corporate_scraper.evaluation import evaluate
from corporate_scraper.models import FieldEvidence


def test_evaluation_reports_metrics_per_field():
    expected = (FieldEvidence("skill_required", "Python", "", "label"), FieldEvidence("education", "Bac+5", "", "label"))
    predicted = (FieldEvidence("skill_required", "Python", "", "exact"), FieldEvidence("skill_required", "Docker", "", "exact"))

    metrics = {item.field: item for item in evaluate(expected, predicted)}

    assert metrics["skill_required"].precision == 0.5
    assert metrics["skill_required"].recall == 1.0
    assert metrics["education"].recall == 0.0

import json
from corporate_scraper.cli import main
from corporate_scraper.store import StudyStore

def test_cli_creates_a_study_from_a_preset(tmp_path, capsys):
    preset = tmp_path / "preset.json"; database = tmp_path / "studies.db"
    preset.write_text(json.dumps({"name":"Morocco","queries":["python"],"cities":["Rabat"],"sources":["linkedin"]}), encoding="utf-8")
    assert main(["--database", str(database), "create-study", "--preset", str(preset)]) == 0
    assert StudyStore(database).run(capsys.readouterr().out.strip())["name"] == "Morocco"


def test_cli_reports_invalid_preset_without_creating_a_study(tmp_path, capsys):
    preset = tmp_path / "preset.json"; database = tmp_path / "studies.db"
    preset.write_text("not json", encoding="utf-8")

    assert main(["--database", str(database), "create-study", "--preset", str(preset)]) == 2
    assert "Preset error:" in capsys.readouterr().err


def test_cli_reports_missing_study_on_export(tmp_path, capsys):
    database = tmp_path / "studies.db"

    assert main(["--database", str(database), "export", "--run-id", "missing", "--output", str(tmp_path / "out.xlsx")]) == 3
    assert "Export error:" in capsys.readouterr().err


def test_cli_reports_missing_study_on_run(tmp_path, capsys):
    database = tmp_path / "studies.db"

    assert main(["--database", str(database), "run", "--run-id", "missing"]) == 4
    assert "Run error:" in capsys.readouterr().err


def test_cli_reports_missing_study_on_resume(tmp_path, capsys):
    database = tmp_path / "studies.db"

    assert main(["--database", str(database), "resume", "--run-id", "missing"]) == 4
    assert "Resume error:" in capsys.readouterr().err

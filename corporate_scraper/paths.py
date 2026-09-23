"""Local, user-owned paths for studies and exports."""
from __future__ import annotations
import os
import json
import tempfile
from pathlib import Path


def data_directory() -> Path:
    """Return a writable per-user location without requiring the UI to start first."""
    preferred = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local")) / "CorporateScraper"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write-probe"
        probe.touch(exist_ok=True)
        probe.unlink()
        return preferred
    except OSError:
        # This is useful for portable installations and restricted corporate
        # profiles. It is intentionally local to the working installation.
        fallback = Path.cwd() / ".corporate_scraper"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

def study_database() -> Path:
    return data_directory() / "studies.sqlite3"


def results_directory() -> Path:
    """The project launch folder owns the default export location and preference."""
    settings_file = Path.cwd() / ".corporate_scraper" / "preferences.json"
    try:
        value = json.loads(settings_file.read_text(encoding="utf-8")).get("results_directory")
    except (OSError, ValueError, AttributeError):
        value = None
    return Path(value).expanduser().resolve() if value else Path.cwd() / "results"


def set_results_directory(value: str) -> Path:
    if not value.strip():
        raise ValueError("Choisissez un dossier de résultats.")
    directory = Path(value).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=directory):
        pass
    settings = Path.cwd() / ".corporate_scraper" / "preferences.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=settings.parent, delete=False) as handle:
        json.dump({"results_directory": str(directory)}, handle)
        temporary = Path(handle.name)
    temporary.replace(settings)
    return directory


def default_export_path(run_id: str) -> Path:
    return results_directory() / f"etude-{run_id[:8]}.xlsx"

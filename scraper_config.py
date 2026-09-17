"""Stage 1 local configuration only; no source adapter or collection policy changes."""

import configparser
import os
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent


def load_settings(path=None, environ=None):
    """Read local settings without printing credentials or making any requests.

    Priority: explicit environment variable > local INI > compatible default.
    Relative proxy paths are resolved beside the INI, not against the launch cwd.
    """
    env = os.environ if environ is None else environ
    config_path = Path(path or env.get("SCRAPER_CONFIG", PROJECT_DIR / "settings.local.ini")).expanduser().resolve()
    parser = configparser.ConfigParser(interpolation=None)
    if config_path.exists():
        try:
            with config_path.open(encoding="utf-8-sig") as handle:
                parser.read_file(handle)
        except (OSError, UnicodeError, configparser.Error):
            # ConfigParser errors can echo the offending line, including a secret.
            raise ValueError("Impossible de lire la configuration locale. Vérifiez son format INI UTF-8.") from None
    username = env.get("GEONAMES_USERNAME", parser.get("geonames", "username", fallback="")).strip()
    proxy_value = env.get("SCRAPER_PROXY_FILE", parser.get("paths", "proxy_file", fallback="IP_proxies.txt"))
    proxy_path = Path(proxy_value).expanduser()
    if not proxy_path.is_absolute():
        proxy_path = config_path.parent / proxy_path
    return {"geonames_username": username, "proxy_file": str(proxy_path.resolve())}


def prepare_tk():
    """Repair Tcl/Tk script discovery for Windows Python virtual environments."""
    if os.name == "nt":
        for key, folder, filename in (("TCL_LIBRARY", "tcl8.6", "init.tcl"), ("TK_LIBRARY", "tk8.6", "tk.tcl")):
            candidate = Path(sys.base_prefix) / "tcl" / folder
            if key not in os.environ and (candidate / filename).is_file():
                os.environ[key] = str(candidate)


def error_kind(error):
    """Safe Stage 1 console diagnostics: exceptions can contain proxy passwords.

    Detailed, redacted structured logging is a later reliability-stage change.
    """
    return type(error).__name__


SETTINGS = load_settings()

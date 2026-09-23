"""Launch the Corporate Scraper v2 desktop application."""

import os
import sys

# A packaged shortcut may choose an arbitrary working directory. Keep the
# portable distribution's results and preferences beside its executable.
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

from corporate_scraper.ui import run


if __name__ == "__main__":
    raise SystemExit(run())

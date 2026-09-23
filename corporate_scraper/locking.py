"""Small cross-process guard for collection ownership."""

from __future__ import annotations

import os
from pathlib import Path


class RunLock:
    """Prevent the desktop and scheduler from collecting into one study store."""

    def __init__(self, directory: str | Path) -> None:
        self.path = Path(directory) / "collection.lock"
        self._held = False

    def acquire(self) -> None:
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            if self._owner_is_active():
                raise RuntimeError("Another Corporate Scraper collection is already active.") from error
            # A previous process died without reaching its finally block. The
            # PID check is deliberately conservative when access is denied.
            self.path.unlink(missing_ok=True)
            return self.acquire()
        with os.fdopen(descriptor, "w", encoding="utf-8") as lock_file:
            lock_file.write(str(os.getpid()))
        self._held = True

    def _owner_is_active(self) -> bool:
        try:
            owner = int(self.path.read_text(encoding="utf-8").strip())
            if owner <= 0:
                return False
            os.kill(owner, 0)
        except PermissionError:
            return True
        except (OSError, ValueError):
            return False
        return True

    def release(self) -> None:
        if self._held:
            self.path.unlink(missing_ok=True)
            self._held = False

    def __enter__(self) -> "RunLock":
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()

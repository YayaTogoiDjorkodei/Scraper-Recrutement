import pytest

from corporate_scraper.locking import RunLock


def test_lock_prevents_second_owner_and_is_released(tmp_path):
    first = RunLock(tmp_path)
    first.acquire()
    with pytest.raises(RuntimeError, match="already active"):
        RunLock(tmp_path).acquire()
    first.release()
    with RunLock(tmp_path):
        assert (tmp_path / "collection.lock").exists()
    assert not (tmp_path / "collection.lock").exists()


def test_stale_lock_is_recovered(tmp_path):
    (tmp_path / "collection.lock").write_text("999999999", encoding="utf-8")

    with RunLock(tmp_path):
        assert (tmp_path / "collection.lock").exists()

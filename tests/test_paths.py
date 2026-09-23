from corporate_scraper.paths import data_directory


def test_data_directory_is_writable():
    directory = data_directory()
    assert directory.is_dir()
    probe = directory / "test-write-probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()

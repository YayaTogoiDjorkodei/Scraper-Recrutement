# Scraper-Recrutement

This project is rebuilding the LinkedIn and Indeed market-research scraper into a Morocco-first corporate desktop application. The existing legacy entry points remain available during the migration. The new PySide6 desktop application, shared collection contracts, transactional study store, fixture-tested adapters, evidence extraction, and Excel export live in `corporate_scraper/`.

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Copy `settings.example.ini` to `settings.local.ini` and set the optional GeoNames username and local proxy-file path. The city chooser loads the complete Morocco city list without an API key from CountriesNow, then keeps an offline cache. `settings.local.ini`, `.env` files and `IP_proxies.txt` are ignored; credentials and proxy endpoints must stay local. Environment variables `GEONAMES_USERNAME` and `SCRAPER_PROXY_FILE` override the INI values.

## Run

```powershell
.\.venv\Scripts\python.exe main.py       # LinkedIn entry point
.\.venv\Scripts\python.exe indeed.py     # Indeed entry point
.\.venv\Scripts\python.exe run_desktop.py # Corporate Scraper v2 desktop UI
.\.venv\Scripts\python.exe -m corporate_scraper create-study --preset preset.json
.\.venv\Scripts\python.exe -m corporate_scraper run --run-id STUDY_ID
```

## Shareable Windows build

Install the development dependencies, then run `.\build_windows.ps1 -Clean`.
The single file `dist\CorporateScraper.exe` is the complete application to share;
the recipient does not need Python installed.
The recipient can copy `settings.example.ini` to `settings.local.ini` if they
need custom settings. Proxy files and credentials are intentionally not bundled.

## Results and saved studies

Excel workbooks now default to `results/` in the folder where you launch the
project. Change the destination under **Paramètres → Résultats Excel**, then
click **Enregistrer le dossier**. This preference is saved locally in
`.corporate_scraper/preferences.json`. The collection screen offers **Ouvrir
Excel** once automatic export finishes.

The jobs sheet contains extracted skills, education, experience, contract and
languages. **Requirements** retains evidence, **Summary** reports coverage,
and **Descriptions** holds the full cleaned text when enabled. Descriptions are
split into numbered parts rather than forcing huge rows in the jobs sheet.
SQLite stores studies for recovery and reprocessing; it is separate from the
Excel output. To refresh an older study without scraping again:

```powershell
.\.venv\Scripts\python.exe -m corporate_scraper reprocess --run-id STUDY_ID
.\.venv\Scripts\python.exe -m corporate_scraper export --run-id STUDY_ID --include-descriptions
```

## Tests

The Stage 1 suite uses synthetic saved HTML and forbids HTTP requests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The v2 desktop and CLI can run the currently verified LinkedIn HTTP path. They
persist results locally, retrieve descriptions, and keep collection responsive
while the worker runs. Indeed currently returns an explicit HTTP 403 in the
workstation feasibility test and is reported as unavailable; it is not bypassed.
Browser fallback, current Indeed support, and a broader source-validation corpus
remain release gates. See the consolidated [v2 plan](docs/CORPORATE_SCRAPER_V2_PLAN.md).

# Scraper-Recrutement

This branch stabilizes the existing LinkedIn and Indeed market-research scraper. The original requests/BeautifulSoup pipeline, Playwright fallback, proxy support, RapidFuzz extraction, Tkinter workflow and Excel export remain the product.

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Copy `settings.example.ini` to `settings.local.ini` and set the optional GeoNames username and local proxy-file path. `settings.local.ini`, `.env` files and `IP_proxies.txt` are ignored; credentials and proxy endpoints must stay local. Environment variables `GEONAMES_USERNAME` and `SCRAPER_PROXY_FILE` override the INI values.

## Run

```powershell
.\.venv\Scripts\python.exe main.py       # LinkedIn entry point
.\.venv\Scripts\python.exe indeed.py     # Indeed entry point
```

## Tests

The Stage 1 suite uses synthetic saved HTML and forbids HTTP requests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

No live LinkedIn or Indeed scrape has been performed as part of this stage.

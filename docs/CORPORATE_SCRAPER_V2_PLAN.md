# Corporate scraper v2: baseline audit and proposed upgrade

Status: proposed; implementation has not started.

Baseline: `43676ab86bc7029ac93442af061476b27606dafb`.
Branch: `upgrade/corporate-scraper-v2`.

## Product contract

The scraping engine is the product. The purpose is IT market studies and recruitment-market intelligence from collected job offers.

The workflow remains:

```text
Search parameters and GeoNames city selection
    -> source-specific requests, proxy and user-agent selection
    -> Requests retrieval -> BeautifulSoup parsing
    -> Playwright fallback when appropriate -> parsing again
    -> field extraction and reference-list/RapidFuzz matching
    -> normalize, validate and deduplicate offers
    -> preview/filter -> market analysis -> Excel/CSV export
```

Local run history supports reopening and resuming market studies. It is not a CRM, candidate-management system or database-centered replacement product. Both existing entry points remain usable throughout the migration. No phase removes Requests, BeautifulSoup, Playwright, proxy support, user-agent rotation, reference matching, GeoNames, background collection or Excel export.

No CAPTCHA solving or access-control bypass will be implemented. Network/proxy failures and explicit source denials must be distinguished: replacing a dead permitted transport is different from trying to evade a source's refusal. An explicit challenge is reported and backs off/stops according to the configured source policy; it must not trigger a silent escalation through proxies or browser identities.

## Inspection performed

Read all three Python scripts in full, both dependency manifests, `.gitignore`, and the historical reference file. Inspected the proxy file's format without displaying addresses or credentials. Inspected both workbook schemas and native table/filter/pane metadata without editing either workbook. Parsed current scripts with Python's AST without importing or executing them.

No live requests were sent to LinkedIn, Indeed, GeoNames or the proxy-test endpoint. No scraper was launched. Browser availability, proxy connectivity and live source access are unverified. Static syntax success is not a successful scrape.

### File inventory

| File | Existing responsibility | Audit finding |
| --- | --- | --- |
| `main.py` | 637-line LinkedIn scraper, parser, matching, worker, city picker, Tk interface, Excel and close-time CSV save | These functions are coupled through module globals and import-time side effects |
| `indeed.py` | 576-line Indeed equivalent | Shared logic is duplicated but source behavior and exports differ materially |
| `procyverification.py` | Load the proxy list, randomly pick one and request `https://httpbin.org/ip` | A real diagnostic capability to integrate into proxy management; currently runs immediately on import |
| `IP_proxies.txt` | Existing authenticated proxy routes | Ten nonempty entries use the expected four-part format; the file is tracked despite the ignore rule; no health test performed |
| `requirements.txt` | Larger dependency manifest | Includes `fake-useragent` but omits `rapidfuzz`; contains packages unrelated to current scripts; UTF-16 |
| `requirements` | Second dependency manifest | Also omits `rapidfuzz`, and does not include `fake-useragent`; UTF-16; diverges from the other manifest |
| `.gitignore` | Ignore local files | UTF-16; excludes `liste.py`, which is required application vocabulary; ignoring the proxy file has not removed its existing tracking |
| `Fichier_Scrapinge_Recrutement.xlsx` | Saved market-study export | `IT Jobs Data`, 120 data rows, 13 columns, 120 hyperlinks; no frozen panes, table or auto-filter |
| `Fichier_Scripinge_Recrutement.xlsx` | Another saved market-study export | `IT Jobs Data`, 54 data rows, 13 columns, 54 hyperlinks; no frozen panes, table or auto-filter |

Both workbook header rows are `A1:M1`: Company Name, Job Title, City / Region, Job Link, Education Level Required, Tech Stack / Skills, Contract Type, Experience Required, Salary, Offer Status, Posted Date, Status / Date Detail, Recruiter Contact. These files are historical evidence of output structure, not proof that the current code still produces that structure or that access works today. The current LinkedIn exporter uses a `source` column where the saved workbooks have `Offer Status`; both distinct concepts must survive the unified schema.

The current interpreter can find requests, bs4, lxml, pandas, openpyxl and tkinter. It cannot find playwright, fake_useragent, rapidfuzz or liste. No dependencies have been installed during this audit.

### Missing reference file

`liste.py` was removed in commit `1343c39`. The prior version is available as `23f5eb8:liste.py` (`1343c39^:liste.py`) and was read without restoring it.

That version contains `technologies`, `niveaux_etudes`, `experience` and `type_contrat`. It turns the technology list into a set, which removes duplicates but makes result ordering unstable. Its vocabulary is broad and should be recovered, versioned and extended, not replaced with a small new list.

`main.py:18` additionally imports `mots_technicien` and `niveaux_master`. Those definitions are absent from the recovered file, and the inspected history search found no definitions in `liste.py`. A newer local copy from the owner is preferred. If none exists, proposed definitions need explicit review because they affect education inference. Simply restoring the historical file would not fully repair LinkedIn startup.

## Existing functions and why they exist

| Function/group | Location | Role and preservation requirement |
| --- | --- | --- |
| `Normaliser` | main:22; indeed:17 | Lowercase, trim, collapse spaces and normalize `bac + 1` to `bac+1`; retain through shared normalization |
| `extraire_correspondances` | main:29; indeed:24 | Exact substring match, then RapidFuzz `partial_ratio` for references at least four characters long, default threshold 88; retain and characterize before improving |
| `detect_security_mechanism` | main:48; indeed:40 | Scan HTML/scripts for challenge indicators; preserve and wire into structured outcomes |
| `charger_liste_ip` | main:77; indeed:68; proxy checker:1 | Load `ip:port:user:password` routes from a local UTF-8 file; preserve input compatibility |
| `charger_villes_geonames` | main:85; indeed:76 | Fetch up to 1,000 populated-place names, sorted and deduplicated; preserve GeoNames while adding configuration/cache/manual city entry |
| `Recherche_par_request` | main:105; indeed:96 | Source query, random proxy and user agent, 15-second request, return HTML or None; preserve Requests-first collection |
| `recuperer_page_playwright` | main:128; indeed:118 | Fetch rendered HTML with Chromium, proxy and user agent when HTTP parsing is insufficient; preserve fallback and source-specific settings |
| `collecter_donnees_brutes` | main:170; indeed:161 | Source selectors, source fields and requirement matching; migrate each parser with fixture comparisons |
| `recherche_thread` | main:249; indeed:231 | Iterate cities/pages, fetch/parse/fallback, accumulate offers, pace requests and report progress; shared orchestration must retain this sequence |
| `Recherhce` | main:302; indeed:282 | Read form values, validate inputs, set button states and launch worker |
| `Arreter` | main:335; indeed:315 | Signal cancellation without blocking the interface |
| `Exporter` | main:342; indeed:332 | pandas/openpyxl export, column mapping, list formatting, styled headers and hyperlinks |
| `Sauvergarder`, `Onclique` | main:439,446 | Protect unexported results when closing; extend this capability to both sources and make failure handling reliable |
| `mettre_a_jour_tags_villes` | main:459; indeed:408 | Show selected cities and allow removing them |
| `Fenetre_Ville` and nested callbacks | main:486; indeed:435 | Filter/search/check cities, scroll the city list and update the count |
| `afficher_ou_masque_panau_ville` | main:563; indeed:513 | Toggle the city-selection panel |
| Module-level Tk construction | main:19,576 onward; indeed:524 onward | Build and run the desktop application; later isolate initialization so tests can import the engine without launching UI/network calls |

### Source differences to retain explicitly

| Behavior | LinkedIn | Indeed |
| --- | --- | --- |
| Endpoint/query | `/jobs/search/`, `keywords`, `location`, `start` | `/jobs`, `q`, `l`, `start` |
| Browser mode | `headless=True` | `headless=False` |
| Browser readiness | `ul.jobs-search__results-list` | Extra 3-second wait, then `div.job_seen_beacon, td.resultContent` |
| Card selection | Every `li`, then checks for LinkedIn child selectors | `div.job_seen_beacon, div.cardOutline` |
| Requirement matching | Calls the fuzzy matcher; technician/master overrides use threshold 85 | Defines the fuzzy helper but the parser uses exact substring comprehensions |
| Pagination currently implemented | `start = page_index * 25` | Also `start = page_index * 25`; this needs source-specific verification, not an assumed replacement constant |
| Excel output | 13 mapped fields, raw clickable URL text | Six selected fields, hyperlinks displayed as `Voir l'offre` |
| Progress/close protection | Indeterminate progress bar and save-before-exit callbacks | No corresponding progress bar or custom save-before-exit handler |

LinkedIn HTTP and browser URLs also differ in ordering: the browser path adds `sortBy=DD`, while the HTTP path does not. This can cause the fallback to retrieve a different ordering of the same search. Initially characterize this behavior; change it in an explicit correctness commit, not as a side effect of moving code.

## Technical debt and consequences

### Startup and data-loss risks

1. Missing vocabulary and missing dependencies prevent a reproducible startup. The two absent education helper lists require clarification.
2. Importing modules creates UI/network side effects. GeoNames is requested synchronously before the usable interface; failure leaves no selectable cities and there is no manual-entry fallback.
3. `toutes_les_donnees` is initialized only in the worker. Exporting or closing LinkedIn before a search can reference an undefined variable.
4. Every new run clears the accumulated offers. There is no run archive or recovery checkpoint.
5. LinkedIn's `Donner_Exporter` is not reset when a new collection starts. A previous export can make later unexported results appear saved.
6. The close dialog saves for both Yes and No. CSV save exceptions are printed, then the window still closes. Close-time data access can also race with the worker. Indeed lacks this protection entirely.

### Collection reliability

7. `random.choice` and four-part proxy parsing occur outside the request handlers' try blocks. Empty/malformed proxy lists can crash the worker before the network-error path.
8. All failures collapse into None/empty lists: connectivity, empty results, changed markup, verification and rendering requirements are indistinguishable. The worker can misleadingly report completion.
9. Challenge-detection calls are commented out in both parsers. Plain indicator scanning also needs false-positive tests: a normal page can contain a CAPTCHA script without presenting a challenge.
10. There is no retry budget, session reuse, health tracking or quarantine. Each HTTP page rereads the proxy list; each fallback starts a fresh browser/context and chooses another proxy/user agent.
11. Cancellation exits only the inner pagination loop; outer-city iterations and `time.sleep` delays continue. Cancellation is cleared inside the worker, creating a potential race with an immediate stop request.
12. Workers directly call Tk `StringVar.set`; cleanup has no outer try/finally. An exception can leave controls disabled or progress running.
13. Page count zero is accepted; non-integer input silently becomes one. Both sources inherit the same offset multiplier without source-specific navigation verification.
14. Browser selector absence returns debug HTML, which can again become an unexplained empty parse. There is no cached-page/repeated-page detection, source cooldown, request accounting or resumable page ledger.

### Extraction and market-study correctness

15. Matching uses unrestricted substring search. Short references such as `C` and `CI`, and embedded names such as Java/JavaScript, can generate false positives. Fuzzy `partial_ratio` on the whole card gives no evidence span or reason.
16. Technician/master overrides can replace all education matches without preserving competing evidence. Reference vocabulary, aliases and thresholds are not versioned with results.
17. Indeed calculates `source` but stores activation status under `sourcev `. Ordinary job-type/insight badges are treated as evidence that the offer is disabled. LinkedIn also conflates some benefit-related elements with closure. Source, availability and extraction quality need separate fields.
18. The current parsers read search cards. They do not retrieve full job-detail descriptions. Requirements not present in a card cannot reliably be detected; description enrichment is an additional, explicitly budgeted collection step.
19. URLs, companies, locations, dates and salaries remain mostly raw strings. Empty fields become `N/A`; no consistent validation, deduplication or normalized analysis model exists.
20. Both parsers accept a record if either title or company is present. Partial records must remain reviewable with reasons; a new validation layer must not silently discard them.

### Interface, exports and configuration

21. UI windows are 500x360 and 500x300 with no results table, analysis workspace or export preview. LinkedIn's mouse-wheel binding passes the callback in the wrong place.
22. Indeed drops extracted fields at export. Both exporters write fixed filenames, can fail on empty results and do not protect prior output with atomic writes or provide usable file-error recovery.
23. Existing Excel styling and clickable links are valuable, but there are no structured tables/frozen headers/filters, analysis sheets or formula-prefix safeguards for scraped text.
24. Credentials, paths, thresholds, delays and timeouts are embedded in code/files. Proxy values must be redacted from diagnostic messages and never added to new commits. Removing existing tracking later must preserve the local file and all proxy functionality; history must not be rewritten without separate authorization.
25. There are no tests, package metadata, README, fixture baseline or deployment instructions for Chromium installation. Several declared packages are unrelated to the inspected code, while required RapidFuzz is missing.

## Proposed target architecture

Use a Python desktop package, introduced one module at a time around the current functions. Keep Tkinter/ttk, Requests, BeautifulSoup/lxml, Playwright, fake-useragent, RapidFuzz, pandas and openpyxl. Keep the current French interface language by default; a language change is a separate product choice.

```text
main.py                         Existing LinkedIn entry point, kept working
indeed.py                       Existing Indeed entry point, kept working
procyverification.py            Compatibility entry for proxy diagnostics
scraper/
  sources/
    base.py                     Provider contract and typed page outcomes
    linkedin.py                 Original LinkedIn query/selectors/parser
    indeed.py                   Original Indeed query/selectors/parser
  collection/
    runner.py                   City/page loop, cancellation, progress, resume
    http.py                     Requests sessions, bounded retries and timeouts
    browser.py                  Playwright fallback and context lifetime
    proxies.py                  Legacy file loading, tests, scoring, quarantine
    pacing.py                   Source budgets, randomized waits and cooldowns
    cache.py                    Bounded page cache and collected-page ledger
  extraction/
    normalize.py                Text, URL, company/location/date normalization
    matching.py                 Exact/alias/fuzzy matches with evidence
    requirements.py             Degree, experience, contract, salary/work mode
    references/                 Recovered vocabulary, aliases and rule versions
  models.py                     Raw observations, normalized offers, run events
  quality.py                    Validation flags and duplicate groups
  analysis.py                   Market aggregates over the active filtered data
  exports.py                    pandas/openpyxl Excel and CSV
  history.py                    Lightweight, versioned local study files
  cities.py                     GeoNames, city identifiers/cache and manual entry
  config.py                     Validated settings and environment overrides
  diagnostics.py                Structured logs with credential redaction
  ui/                           Tk shell, six views, tables and detail panels
tests/fixtures/                 Source HTML with no credentials/personal sessions
```

The provider contract owns source URL construction, selectors, page navigation and source defaults. The runner owns fetch/parse/fallback order and emits structured events. The HTTP/browser transports share validated proxy configuration but do not mix cookies across identities; a browser context belongs to its source/route/user-agent session. Rotation remains available, with its cadence made explicit rather than accidentally changing identity on every operation.

Two separate refactor steps are essential: first move existing code with fixture-equivalent behavior; then improve policies/parsing in separately reviewable commits. Defaults such as headless mode, request parameters and matching thresholds must be preserved during the move. Intentional correctness changes get their own tests and documented before/after behavior.

### Data and study files

Keep raw source observations, normalized values and matching evidence distinct. A detected field should retain its source text/snippet, canonical value, method (`exact`, `alias`, `fuzzy`, `pattern`, or explicitly `inferred`), score where applicable, and rule/reference version. Scores describe matching evidence, not calibrated probabilities.

A study contains run parameters, source/transport outcomes, collected-page checkpoints, raw observations, normalized offers, rejected/partial records with reasons, duplicate groups, active filters and collection timestamps. Start with atomic JSON manifests and JSONL records in a local study directory; use bounded optional HTML caching. No database is necessary for this phase. Propose a storage change only if measured size/performance requires it.

Deduplicate exact source IDs/canonical URLs first. Cross-source company/title/location similarity produces explainable duplicate groups and conservatively flags ambiguous matches. Keep all source observations and allow the analyst to see source appearances versus unique offers; do not silently merge distinct vacancies or delete duplicates from the evidence.

### Collection policy and progress

Default to one active source worker, matching the current serial collection model. Apply configurable per-source request budgets, randomized delays, bounded retries and interruption-aware waits. A completed-page ledger prevents revisiting pages within a run; a cache key includes query, city, page, source and relevant transport context. Refreshing a new study must remain possible and explicit cache timestamps distinguish cached from newly fetched data.

Retain Requests-first and Playwright fallback for pages needing rendering or otherwise eligible for fallback. Separate confirmed empty pages, layout failures, transport errors and explicit source blocks. Honor cooldowns and avoid repeated requests to an explicitly blocked source. Health tests should be explicit, bounded and cached; measure latency/failures and distinguish a globally dead proxy from a route that is blocked only for one source. Display proxy aliases, never passwords.

Live collection events include source, city, page, transport, current step, offers observed/accepted/partial/rejected, duplicates, proxy alias/health, retries/errors, elapsed time and cancellation state. Unknown total page counts must not be presented as precise completion percentages. Save completed pages as checkpoints and clearly label partial/cancelled runs.

### Desktop workflow

| View | Main purpose |
| --- | --- |
| Search / Collection | Keywords, source selection, GeoNames/manual cities, page budget, settings preset, start/stop, live collection and proxy status |
| Results | Search/filter/sort, selectable columns, pagination, source/quality indicators, details/evidence and original offer links |
| Analysis | Charts and tables computed from the same active filtered dataset, with sample counts and missing-data coverage |
| Exports | Column/sheet selection, filtered/all/selected scope, destination preview and Excel/CSV generation |
| History / Logs | Reopen saved studies, view outcomes and redacted logs, resume eligible unfinished pages |
| Settings | GeoNames configuration, local proxy file, proxy tests/status, thresholds, browser mode, pacing, timeouts, cache/retention and export defaults |

Use a consistent type scale, spacing, restrained colors and readable ttk tables, with keyboard navigation and responsive resizing. Data acquisition remains central: opening the application leads to search/collection, not a generic dashboard. UI redesign comes after the current scrapers run through the shared engine successfully.

### Market analysis

Provide offer counts by city, source, company, role/title, technology, education, experience band, contract and work mode; common technology pairs/combinations; and posting/collection-date distributions where available. Keep verbatim titles alongside optional role groups.

Salary summaries must group compatible currency, period and pay-basis values, show coverage/sample counts, and avoid silently mixing annual/monthly, gross/net or different currencies. Publication date, collection date and first-seen date remain separate. Trends require comparable saved studies and visible differences in source/query coverage. All summaries describe the collected sample; missing source coverage cannot be hidden by showing a plausible market total.

### Excel and CSV

Preserve pandas/openpyxl and every legacy field, then add normalized source/work-mode/salary/date/quality fields. Export raw URLs as values plus usable hyperlinks; support legacy `Voir l'offre` hyperlinks when reopening old studies/exports. Provide structured offer tables, filters, frozen headers/identifying columns, suitable widths/wrapping and optional analysis/evidence/methodology sheets. Use atomic writes and protect against formula-like scraped text. Export the active filtered dataset consistently across offers and analysis, with an explicit option for all/selected rows.

## Phased implementation and independent checkpoints

Each stage is a separate logical commit, or a short sequence of independently reversible commits for the larger stages. Never combine a parser move, new matching policy and UI replacement in one commit.

| Stage | Deliverable | Acceptance gate |
| --- | --- | --- |
| 0. Audit and plan | This document only, on the new branch | Original source/config/workbook files unchanged; user reviews the plan before implementation |
| 1. Reproducible baseline | Recover original references; resolve missing helper definitions; correct UTF-8 dependency manifest, Chromium setup and configuration examples; isolate testable functions; basic fixture characterization | Both entry points start in a fresh environment with configured GeoNames/proxies; original Requests/Playwright paths and source differences are testable; no fabricated live-success claim |
| 2. Incremental source adapters | Move LinkedIn and Indeed parsing/query logic separately; introduce shared runner/transports while keeping existing Tk screens wired to them | Fixture outputs match the recorded baseline, including intentional legacy quirks until fixed separately; both sources still execute Requests first and eligible browser fallback |
| 3. Reliability and diagnostics | Proxy pool/health, retries/backoff, session/browser reuse, pacing, typed outcomes, cancellation/finally cleanup, bounded caching and redacted logs | Simulated success, empty results, malformed cards, timeouts, failed proxies, block/429, fallback and cancellation behave predictably; partial offers survive failure; source denial is never treated as an invitation to bypass |
| 4. Extraction and data quality | Canonical schema, recovered/expanded references and aliases, evidence-bearing RapidFuzz/pattern matching, source/status fixes, normalized fields and duplicate groups | Labelled fixtures test precision and recall, short-token false positives, degree/experience overlap and cross-source duplicates; raw values/observations remain accessible; every output difference is intentional |
| 5. Lightweight study history | Atomic local run saves/checkpoints, reopen, retention and bounded cache, save-before-exit for both scrapers | Save/reopen round-trips preserve offers, sources, evidence, filters and parameters; cancellation/crash recovery does not overwrite another study; resume avoids known completed pages |
| 6. Professional Tk interface | Six requested views, live run telemetry, results controls/details, GeoNames/manual cities and proxy-health display | The redesigned screens use the already-verified scraper services; main-thread UI updates only; resize/keyboard/empty/error/busy/cancel states and save-before-exit are tested |
| 7. Market-study analysis | Counts, distributions, technology combinations, compatible salary cohorts and supported date trends | Hand-calculated sample expectations agree; filtering changes results and analysis consistently; sample size, unknowns and source coverage are visible |
| 8. Export completion | Full-schema Excel/CSV, structured tables, frozen panes, filters, optional analysis/evidence and atomic writes | Both original output schemas remain compatible; URLs and all extracted fields survive; filtered counts reconcile across sheets; empty/partial results, locked files, accents and formula-like text are tested |
| 9. Packaging and release checks | Clean install/startup, README, architecture/configuration/usage guide, pinned tested dependencies, CI and optional Windows executable packaging | Fresh-environment setup includes Playwright Chromium; bundled vocabularies and runtime paths work; no credentials in new tracked files; tests pass; actual live-source verification is reported separately from offline tests |

Some safeguards (initializing run state, fixing unsafe close behavior and handling absent configuration) can land as small prerequisite fixes in Stage 1. They must not be concealed inside a large architecture change. Add tests as each boundary is introduced; do not wait for Stage 9 to start testing.

## Test strategy and evidence

- Characterize original parsers, mappings and fallback orchestration with source HTML fixtures before moving them. Synthetic fixtures must be clearly labelled as synthetic, not presented as scrape results.
- Use mocked Requests and Playwright boundaries for network failures, timeouts, source-block signals, proxy selection, pagination, browser cleanup and cancellation. Include a test proving eligible HTTP insufficiency still invokes Playwright and one proving source denial does not trigger bypass attempts.
- Label expected extraction evidence for short symbols, accented text, aliases, fuzzy near-misses, overlapping degrees, experience ranges, remote/hybrid markers, salaries and unknown values. Track precision/recall on that labelled sample rather than reporting a match score as accuracy.
- Check exact and candidate duplicate decisions while retaining original rows and source provenance. Include same-title vacancies with distinct IDs and materially different locations.
- Test study persistence/resume and active-filter consistency. Test Excel structure and hyperlink targets through save/reopen; cover zero rows, partial rows, non-ASCII values, large exports and filesystem failures.
- Exercise Tk worker-to-main-thread events, results table operations, cancellation, failed-run cleanup, unsaved-data close decisions and useful minimum window sizes.
- Run limited, explicitly identified live verification only in a configured environment. Record source, time, route alias, HTTP/browser path and outcome; a successful run on one source/route does not establish all routes or future access.

## Review checkpoint and unresolved input

The only change in this stage is this audit/plan. No application rewrite, dependency installation, proxy change, workbook change or live collection is part of this stage.

Before Stage 1, confirm whether a newer original `liste.py` exists with `mots_technicien` and `niveaux_master`. If unavailable, review their replacement definitions before enabling the original education-override logic. The recovered four main vocabularies are available in Git and should form the baseline either way.

Description/detail-page enrichment materially increases request volume. The proposal is to keep current search-card collection as the default and add enrichment as an explicit, paced, cached option; settle its default before implementing it. Similarly, any change to proxy failure policy, source browser defaults or cross-source fuzzy auto-merging must be presented with its behavioral effect rather than introduced silently.

Implementation waits for review of this plan, as requested.

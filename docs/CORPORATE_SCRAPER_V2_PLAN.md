# Corporate Scraper v2 — authoritative delivery plan

## Product boundary

Corporate Scraper is a Morocco-first Windows desktop application for collecting
public IT-job-market data, reviewing evidence in each description, and exporting
the collected study. It is not a candidate CRM, outreach system, CAPTCHA solver,
or access-control bypass tool.

The product keeps LinkedIn and Indeed as adapters. LinkedIn's HTTP path is
currently verified on this workstation. Indeed returned HTTP 403 during a
bounded test and is reported unavailable until normal public access can be
verified again. Browser fallback is not enabled until a real-browser inspection
records stable, sanitized fixtures.

## Current implementation status — 2026-09-19

| Area | State | Evidence |
| --- | --- | --- |
| Desktop UI | In progress | PySide6 five-workspace application, visible live stage/progress indicators, responsive collection worker, results/detail review, history, settings, in-app export |
| Morocco city selection | Implemented | Searchable multi-select picker, 242 unique-city keyless CountriesNow refresh verified on this machine, and offline local cache |
| LinkedIn HTTP collection | Implemented | Search and detail HTTP 200 validation; target-one end-to-end run reached its target in two requests |
| Indeed | Unavailable | Public search received HTTP 403; no bypass, retry storm, or identity switching |
| Run engine | Implemented | Shared runner, per-source session reuse, paced target/budget controller, pause/stop, resume-safe checkpoints, process lock |
| Persistence | Implemented | SQLite runs, tasks, observations, offers, evidence, migration-safe schema updates, local history |
| Description extraction | In progress | Evidence for skills, education, experience, contract, language, and work mode; requirement filters and unknown-value policy |
| Results and export | In progress | Source/location/text filters, live company/city/skill summaries, evidence detail, qualification status, automatic background Excel export, manual Excel copy, CLI export |
| Scheduling | In progress | Headless create-study, LinkedIn run, and export commands; Windows Scheduler guide |
| Performance | Partially verified | 10,000-row metadata filter: 31 ms; standard 10,000-row workbook: 27.379 s |

Run `python -m pytest -q` for the current offline/Qt suite. The baseline at the
end of the current implementation batch is 80 tests plus 28 legacy subtests.

Live desktop startup restores the latest saved study instead of showing fixture
rows. Unexpected collection failures leave a visible error and access to saved
results; a second study cannot replace an active collection or automatic export.

The September 19 core repair decodes escaped HTML before extraction, preserves
the original stored description, and commits extracted skills, experience,
contract and education to the offer record alongside evidence (schema v3).
French/English experience patterns and explicit degree phrases are covered.
Bare job titles do not establish a diploma; ambiguous technology aliases and
company-history/contract false positives have regression coverage. A complete
reviewed precision/recall corpus remains outstanding; coverage is not accuracy.

Excel uses one table filter per range: the former overlapping sheet AutoFilter
and table AutoFilter caused native Excel opening/repair failures. Full text is
now in a separate Descriptions sheet with bounded, numbered parts; the jobs
sheet groups skills, education and experience beside company and role.
Default output is `results/` under the launch directory, editable and persisted
in Settings. Existing saved studies can be reprocessed without fetching again.

Validation on this machine: all three regenerated workbooks (60, 100 and 289
offers) opened read-only in native Excel through the normal open path, without
repair mode. The 289-offer study has 286 descriptions, skills detected in 247
offers, education in 142, experience in 176, and contract in 32. These are
coverage counts, not measured precision/recall. Source text and evidence remain
available for review. Workbook ranges for every sheet were rendered and checked.

## Historical Stage 1 baseline

Stage 1 restored the original vocabulary and the two small legacy education
override lists, added safe local configuration, and recorded a tested Windows
dependency set. The original `main.py` and `indeed.py` launchers remain for
compatibility, while their parser behavior is covered by offline fixtures.
Known prototype limitations are documented in the test suite rather than
silently preserved as v2 behavior.

## User workflow

1. **Nouvelle recherche**: choose queries, Moroccan cities, source, target,
   target mode, budgets, and optional requirement filters.
2. **Collecte en cours**: monitor Found → Unique → Descriptions → Matching
   target; pause after the active operation, stop safely, or wait for a source
   outcome.
3. **Résultats**: filter, sort, select, inspect complete descriptions and
   supporting evidence, then open the original offer only by user request.
4. **Historique et planification**: reopen a persisted study or schedule the
   documented headless commands.
5. **Paramètres**: inspect local database location and future transport,
   browser, and export defaults.

Studies persist locally without requiring export. On normal desktop completion,
an Excel workbook with descriptions is generated in the configured `results` folder
in the background; users can also make another copy from the collection or
results view. Every write is atomic.

## Architecture

```text
PySide6 UI or headless CLI
          ↓
CollectionRunner — target, budget, duration, pause/stop, checkpoint policy
          ↓
Source adapters + per-source Requests session
          ↓
observations → exact source-ID deduplication → detail retrieval
          ↓
description extraction + filter qualification + evidence
          ↓
SQLite store → results, summaries, Excel export
```

Qt imports stay in `corporate_scraper.ui`; the runner is reusable by the CLI.
Each source owns one Requests session. Source operations remain bounded and
serial per source; the current release does not add same-source request bursts,
Redis, distributed queues, stealth plugins, or CAPTCHA solving.

## Core rules

- **Unique-listing target:** select at most N source-unique listings; preserve
  later observations as overflow and enrich the selected set within budget.
- **Description target:** keep discovering and enriching until N selected,
  qualifying offers have readable descriptions or a completion limit is met.
- Deduplicate by `(source, source job ID)` or canonical URL. Similar jobs from
  different sources remain separate review candidates.
- Requirement filters are evaluated after description extraction. A missing
  requested value is `unknown` and does not count by default; users may include
  unknown values explicitly. A conflicting explicit value is `excluded`.
- Evidence remains source text. The engine never infers a degree, language,
  experience band, or requirement that the source did not state.
- Source denials stop that source. Direct access is never silently substituted
  for a configured proxy route, and no identity is rotated to evade a denial.

## Data contracts and storage

`RunSpec`, `FilterSpec`, `FetchOutcome`, `JobObservation`, `FieldEvidence`,
`RunCounters`, and `RunEvent` define the engine boundary. SQLite stores the run specification,
completed page/detail tasks, offers, qualification status, descriptions, and
evidence in transactions. Schema versions are persisted and the current store
migrates the qualification-status field for existing v2 databases.

The default workbook contains **IT Jobs Data**, **Requirements**, **Summary**,
and **Run Info**, plus **Descriptions** when full text is enabled. It uses tables, frozen headers, hyperlinks, wrapped text,
formula-safe scraped values, and atomic replacement. Results can export all
selected study offers, with complete descriptions optional. Desktop export is
explicitly the whole study, avoiding accidental single-row exports from the
automatically selected review row; the export service also accepts explicit IDs.

## Verification records

The source evidence and bounded HTTP results from this workstation are recorded
in the source section below. The workstation performance measurements and
evaluation protocol are also consolidated here. Neither record is a promise
that a source will remain available.

## Remaining delivery sequence

### 1. Complete source resilience

- Capture sanitized rendered HTML fixtures with a connected browser.
- Verify LinkedIn paging and no-result/layout states. Repeated-page detection
  is already implemented and fixture-tested.
- Recheck Indeed only through normal public navigation; keep it unavailable if
  it still denies access.
- Add eligible Playwright fallback only for a documented rendering-needed
  outcome, with one reused context per source and bounded navigation budget.

### 2. Complete data quality

- Build a reviewed corpus of 100 representative descriptions, reserving 30 for
  evaluation. The per-field metrics utility and protocol below are ready; the
  human-labelled corpus remains outstanding.
- Measure precision and recall for explicitly stated requirements per field;
  target at least 95% precision and 85% recall.
- Add source-specific publication date, salary, contract, and work-mode
  normalization only when supported by fixtures.

### 3. Complete results experience

- Add filtered export scope and saved summary views. Current row selections
  export only the selected persisted offers; without a selection, all selected
  offers in the study export. Column order and widths are saved locally.
- Add lightweight company, city, role, and skill summaries from the same active
  result filter service.
- Cover failed-save, failed-export, partial, paused, and unavailable-source UI
  states with Qt interaction tests.

### 4. Complete scheduling and release operations

- Implement a `resume` command that reuses the original immutable study spec.
- Add timestamped scheduler output and visible run-failure history.
- Test an interactive and headless Chromium installation separately.
- Add a clean-install check and operating guide.

## Acceptance gates

- 10,000-offer studies: first results visible and common metadata filtering in
  one second; standard workbook in 30 seconds; no unbounded queues/pages/full
  descriptions. The current local model/filter/export benchmarks meet the first
  three measured checks.
- Target counts, result filters, summaries, and exports must agree.
- Pause/stop must acknowledge immediately; network cancellation may wait for
  the configured current-operation timeout and must explain that state.
- Every source behavior claim must have a dated fixture or bounded validation
  record. A source error or denial is a valid terminal outcome.

## Interface specification

The application opens on **Nouvelle recherche** with a persistent sidebar for
Nouvelle recherche, Collecte en cours, Résultats, Historique et planification,
and Paramètres. The search form is grouped into Recherche, Objectif, Exigences
facultatives, and collapsed Options avancées. The default target is 200 and the
range is 1–10,000. LinkedIn is shown as HTTP verified; Indeed is shown as
currently unavailable and is opt-in until its access is verified.

The city field opens a searchable, multi-select Morocco picker. It refreshes a
complete 242-unique-city list from CountriesNow without an API key, caches it locally,
and continues to work from that cache when offline. The collection view shows
Found, Unique, Descriptions retrieved, and Matching target, a green progress
bar based on committed target progress, and clear Discover → Describe →
Qualify → Complete stage cards. It explains target meaning, attempts, source
messages, pause, resume, stop, partial completion, and source denial. A
retrieved description remains visible even when a filter makes it `unknown` or
`excluded`; completion names that outcome and its counts. The collection screen
includes direct **Voir les résultats** and **Exporter Excel** actions. Results use a filter panel, a
virtualized Qt table, and a detail pane with full description, qualification,
evidence excerpts, and an explicit original-link action. Company, city, and
skill summaries use the same rows as the table. Column order and widths are
saved locally, and export can be limited to selected rows or include complete
descriptions.

The visual system is light-first: dark navy navigation, white panels, dark
body text, blue primary actions, visible keyboard focus, and text labels paired
with status colors. Light controls explicitly set their foreground and
selection colors so Windows palette differences cannot produce white-on-white
text. The normal window is 1280×800 and remains usable at 1024×700.

## Source evidence and operating commands

The bounded 2026-09-18 workstation checks found LinkedIn search HTTP 200 with
60 parsed cards and a detail HTTP 200 with a 3,680-character description. A
target-one run reached its target in two requests and produced 32 evidence
items. Indeed returned HTTP 403 and is recorded as unavailable. No browser
fallback or source-denial bypass is enabled.

Headless operations are:

```powershell
.\.venv\Scripts\python.exe -m corporate_scraper create-study --preset C:\path\preset.json
.\.venv\Scripts\python.exe -m corporate_scraper run --run-id RUN_ID
.\.venv\Scripts\python.exe -m corporate_scraper resume --run-id RUN_ID
.\.venv\Scripts\python.exe -m corporate_scraper export --run-id RUN_ID --output C:\path\market.xlsx
```

Exit codes are 0 for success, 2 for an invalid preset, 3 for export failure,
and 4 for run/resume failure. A local process lock prevents desktop and
scheduler overlap. No schedule is enabled during installation.

## Workstation performance evidence

Using 10,000 synthetic persisted offers on the local workstation: Qt model
creation was under 1 ms, a common metadata filter took 31 ms, and the standard
workbook export took 27.379 seconds (505,058 bytes). This validates local UI
and export gates, not network throughput or source availability.

## Extraction evaluation protocol

Before claiming production accuracy, create a human-reviewed corpus of 100
Morocco-relevant descriptions and reserve 30 for evaluation. Label field,
canonical value, and a supporting excerpt for skill_required,
skill_preferred, education, experience, contract, language, and work_mode.
`corporate_scraper.evaluation.evaluate` reports precision and recall per field.
The release target is at least 95% precision and 85% recall for explicitly
stated requirements; fuzzy scores are not accuracy.

## Historical baseline

Stage 1 snapshot notes remain in `docs/STAGE1_BASELINE.md`. The original Tk
launchers remain available during migration; `run_desktop.py` is the v2 Qt
entry point.

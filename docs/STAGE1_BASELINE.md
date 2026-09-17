# Stage 1 — Stabilization baseline

Stage 1 is intentionally incremental. It restores missing runtime inputs and adds an offline safety net without refactoring the scraper core.

## Changes

- Restored `liste.py` from commit `23f5eb8` (467 technologies, 40 study levels, 49 experience values, 25 contract values).
- Added `reference_overrides.py` with the two missing, deliberately small lists used only by LinkedIn's existing education override: `mots_technicien = ["technicien", "BTS", "DUT", "DTS"]` and `niveaux_master = ["master", "MBA"]`. Numeric BAC levels are intentionally excluded because the old fuzzy threshold would misclassify them.
- Added `scraper_config.py` and `settings.example.ini`; GeoNames and proxy paths can be supplied through ignored local configuration or environment variables.
- Repaired dependency manifests, including the missing Playwright, fake-useragent and RapidFuzz packages; `requirements-lock.txt` records the tested Windows/Python 3.13 resolution.
- Kept both `main.py` and `indeed.py` entry points and their parsing functions intact. Proxy support remains; the checked-in proxy file is removed from version control while any local copy remains usable.
- Added synthetic LinkedIn/Indeed/challenge/empty-selector fixtures and tests for parser output, normalization, fuzzy thresholds, security markers, proxy-line handling, Excel field mapping, and save-before-exit.

## Existing behavior documented by tests

The tests preserve several prototype behaviors rather than silently changing them: Indeed uses substring extraction instead of the fuzzy helper; malformed proxy lines are accepted until request time; parser text with accented characters can be mojibake; LinkedIn's close handler saves even when the user answers No; and module initialization performs GeoNames loading before the Tk window. These are candidates for later stages, not Stage 1 rewrites.

Tests use only local fixtures and explicitly fail if a network request is attempted.

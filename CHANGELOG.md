# Changelog

All notable changes to this project will be documented in this file.

## [1.1.3] - 2026-07-08

### Fixed
- CI `.gitignore` contained `.coupon_history.json` (untracked + gitignored), causing `git add` to exit 1 and blocking the entire commit step — `data.csv` never got pushed to the repo

### Chores
- Remove `.coupon_history.json` from `.gitignore` and re-track it; `git add` now succeeds and the daily workflow pushes commits again

## [1.1.0] - 2026-07-01

### Added
- `--yes` / `--non-interactive` flag for CI / automated usage
- `--export-json FILE` — export all coupons as JSON
- `--export-md PATH` — export all coupons as Markdown (not limited to top 50)
- All export flags use `PATH` metavar (was `FILE`) to clarify full path is required
- `--quiet` / `-q` — suppress banner, disclaimer, source line, and bottom tips
- `requirements-lock.txt` — pinned dependency versions for reproducible installs
- `latest_data.json` now tracked in git (removed from `.gitignore`) for reliable `--diff`
- Dynamic section name resolution via API `couponActivityName` for unknown sections

### Changed
- `--top` now respects `--min-rate` and `--brand` filter options
- `--section` name keyword matching now shows **all** matching sections (previously only the first)
- `--diff` differentiates between first run (no history) and corrupted history file
- Argument validation (`--combo -1`, `--min-rate -5`, etc.) now happens **before** data loading, preventing spurious banner output
- "来源" (source info) lines now respect `--quiet` flag
- `print_diff()` error handling split into `FileNotFoundError`, `json.JSONDecodeError`, `OSError` with distinct messages
- `_save_history()` wrapped in try/except to prevent crashes on unwritable paths
- `format_amount()` handles missing or zero `couponDiscount` without showing "0折"
- All export paths (`--export`, `--export-csv`, `--export-json`, `--export-md`) catch `OSError`/`PermissionError`
- `parse_coupons()` guards against non-dict `couponModelVOListMap` values
- `_git_pull_data()` outputs stderr details on failure
- Data expired prompt skipped automatically in `--quiet` mode
- Cron schedule in GitHub Actions adjusted to UTC+8 23:45

### Fixed
- `--combo 0` and `--combo -50` now properly rejected (must be > 0)
- `--min-rate 200` no longer claims "无券可匹配" for non-filtering commands like `--stats`
- `--brand ""` (empty string) now shows a warning instead of silently skipping filter
- Fallback `Console` class (when Rich not available) now has `width` attribute
- Various crashes on corrupted/missing files, unwritable paths, and unexpected API data

### Chores
- Updated `data.csv` with fresh API data (600 rows)
- Internal comment markers upgraded to visible `# ═══` style + TOC index

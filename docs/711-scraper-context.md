# 711 Dashboard Scraper — build context

## How to use this doc
This file is the **orders and rules** for Track A. Your side (a human plus an AI) owns all
site discovery and the implementation: you log into the real dashboard, find the selectors,
determine the login/CAPTCHA behavior, and answer O1–O6 yourselves, then fill `.env` and
`NOTES.md`. The backend team does not have or need those site details; they only need you to
return data that obeys the `OrderToReport` contract below. Follow the rules exactly and the
two halves merge on one line.

## What you are building and why
You are building ONE component of an "order-inform" automation system. A Telegram bot (built by
another person) already captures each order when a seller posts it, and stores the customer's
screenshot keyed by an order code. A reconcile loop needs to know, several times a day, WHICH
orders are currently in a saved filter called `đơn cần báo` ("orders that need informing") on an
internal shipping dashboard (a Taiwan 7-Eleven / forwarder web app). That dashboard has no API,
so your job is to READ that filtered list with Playwright and return it as structured data.

Being in the `đơn cần báo` filter is itself the signal "this order has arrived and the customer
has not picked it up yet." You do NOT compute status. You just return the rows in the filter.

## The ONE interface you implement
File: `src/scraper/seven_eleven.py`. Implement `SevenElevenScraper(BaseScraper)` from
`src/scraper/interface.py`. Do not modify `interface.py`. The interface:

```python
@dataclass(frozen=True)
class OrderToReport:
    stt: str                          # REQUIRED join key, trimmed string, EXACTLY as shown (never int-cast)
    sale_name: str                    # REQUIRED "Sale phụ trách" name, trimmed + whitespace-collapsed, keep case
    s_code: str | None = None         # OPTIONAL "Sxxxx"/"Lxxxx" if on the list, uppercased+trimmed, else None
    group_symbol: str | None = None   # OPTIONAL "Ký hiệu nhóm" if on the list, else None
    raw: dict = ...                   # OPTIONAL extra columns, debugging only

class BaseScraper(ABC):
    @abstractmethod
    def fetch_orders_to_report(self) -> list[OrderToReport]: ...
```

Normalization (MUST match the backend exactly). Helper functions are provided in
`interface.py` — use them: `norm_stt`, `norm_sale_name`, `norm_s_code`.
- `stt = value.strip()` — keep as displayed, never convert to int.
- `sale_name = " ".join(value.split())` — trim + collapse internal whitespace, keep case.
- `s_code = value.strip().upper()` or `None`.

`fetch_orders_to_report()` must:
- Log in (reusing a saved session when possible), open the `đơn cần báo` filter, read **all**
  rows (follow pagination if any), and return one `OrderToReport` per row.
- Be READ-ONLY and idempotent. Never click anything that creates, edits, or deletes on the site.
- Raise `LoginError` / `CaptchaError` / `ParseError` on failure. Never return a partial list
  silently — if you cannot read the whole filter, raise.

## Inputs (from environment, via `src/config.py`)
`SEVEN_ELEVEN_URL`, `SEVEN_ELEVEN_USER`, `SEVEN_ELEVEN_PASS`,
`SEVEN_ELEVEN_STORAGE_STATE` (path to a Playwright `storage_state.json`, default
`.auth/711_state.json`), `HEADLESS` (default `true`). Read them through
`src.config.get_settings()` so both halves share one config source.

## Session & CAPTCHA strategy
- First run: launch **headful** (`HEADLESS=false`), log in by hand if there is a CAPTCHA, then
  save `context.storage_state(path=SEVEN_ELEVEN_STORAGE_STATE)`.
- Later runs: load that `storage_state` and go straight to the filter. Detect a logged-out state
  (redirected to login) and re-login; if a human CAPTCHA is required, raise `CaptchaError` and
  stop so a human can refresh the session.
- **If you discover a CAPTCHA on every lookup (not just login), STOP and report it** — that
  changes the whole design and must be escalated, not worked around.

## Things to confirm on the real site, and write into `NOTES.md`
- **O1** the exact login URL and flow; whether a CAPTCHA appears only at login or on every lookup.
- **O2** whether `STT`, `Sale`, and the `S` code are on the list itself, or only on each order's
  detail page. Prefer reading the list. Only open detail pages if the list lacks a needed field.
- **O3** whether `STT` is globally unique or repeats per Sale (tell the backend; it flips one flag).
- **O4** whether the `Sxxxx` code is shown on the dashboard at all.
- Pagination style, row selector, and how "Sale" and "STT" columns are labelled.

## Error handling & debugging
- Subclass the provided errors. On `ParseError`, save the current page HTML and a screenshot to
  `debug/` with a timestamp so selectors can be fixed fast.
- Anchor selectors on stable things (column headers, `aria`/roles, table structure, text), not on
  auto-generated CSS class names.
- Retries with backoff on navigation/timeouts; a sane per-run timeout.

## CLI + tests (Definition of Done)
- `python -m src.scraper.seven_eleven --dry-run` prints the parsed list as JSON. Against the real
  site it returns ≥1 order.
- Save one real (sanitized) list page to `tests/fixtures/dashboard_sample.html` and write a test
  that parses it offline into `OrderToReport` objects, so selector regressions are caught without
  the live site.
- `NOTES.md` records the confirmed answers to O1–O4 and the selectors used.

## Explicitly NOT your job (owned by the backend, do not build)
- The Telegram bot, the database, the reconcile loop, the notifier, the scheduler.
- Do not change `src/scraper/interface.py`. Do not write to or modify anything on the 711 site.

## Tech
Python 3.10 (the target machine has 3.10.12). The interface uses `from __future__ import
annotations`, so `str | None` and `list[...]` annotations work on 3.10. Playwright for Python is
already installed on this machine (v1.58, chromium cached), so no install is normally needed;
`python -m playwright install chromium` is idempotent if it is. Keep the module importable (the
backend imports your class) AND runnable as a `--dry-run` CLI.

## Reference implementation to crib from
`~/PKBot/services/tcg_playwright_service.py` is an existing "log into a web app, then scrape"
Playwright flow on this same machine and is the closest analog to your task;
`~/PKBot/services/playwright_service_continuous.py` shows a long-running variant. Reuse the
login/session shape, not the target site. PKBot is very large (multi-GB, bundled browsers) — read
those two files for pattern, do not clone the repo.

## Sync-tools with the backend so merging is trivial
- Import the class the backend expects: `from src.scraper.interface import (BaseScraper,
  OrderToReport, LoginError, CaptchaError, ParseError, norm_stt, norm_sale_name, norm_s_code)`.
- Expose a `build_scraper() -> SevenElevenScraper` factory or a plain constructor that takes no
  required args (reads config itself), so `src/reconcile.py` can swap `MockScraper()` for
  `SevenElevenScraper()` on one line.
- `fetch_orders_to_report()` is synchronous in the interface. If you implement with async
  Playwright internally, wrap it (e.g. `asyncio.run`) so the public method stays synchronous.

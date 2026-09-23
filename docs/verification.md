# Verification record

Verified locally on 2026-09-23 using Python 3.14 on macOS. This record reports bounded checks, not a guarantee for arbitrary datasets or every platform.

## Passed

- `python3 -m unittest discover -s tests -v`: **37 tests passed**. Covers known-answer returns, sample volatility, correlation, CAGR, drawdown, weight normalization, terminal allocation drift, exact date alignment and selected-asset behavior; invalid schemas, dates, timestamps, numeric values, settings, size/row/asset bounds; report escaping, CLI imports/exports, overwrite protection; HTTP host/origin/token controls, JSON shape validation, CSV payload imports, request-size boundaries and static route allowlisting.
- `ruff check market_observatory tests scripts`: passed.
- `node --check market_observatory/static/app.js`: passed.
- `node --test tests/browser_csv.test.cjs`: **2 tests passed**, exercising the production decoder on UTF-8 with/without a byte-order mark, LF/CRLF/CR newlines, and malformed UTF-8 rejection.
- Wheel built with setuptools 84.0.0, installed into a clean virtual environment with no runtime dependencies. Installed CLI generated a 300-observation report from a directory outside the checkout. Installed HTTP server supplied HTML, JavaScript and the bundled CSV/metadata successfully.
- `scripts/generate_demo.py` regenerated `data/demo.csv` byte for byte. Canonical demo data SHA-256: `d849246e0675b4733ec1d27f5629df822ee0f208685caebae3949473d08e788b`.
- Chrome desktop visual inspection: full synthetic dataset loads, source/as-of labels visible, metric cards and charts render, buy-and-hold control changes results, and keyboard Home on the chart selects the first observation. No application console errors observed; an unrelated browser extension logged a listener error.
- Chrome responsive inspection at **390 × 844**: document width equals viewport width (390 px), without page-level horizontal overflow. Temporary viewport override reset afterward.
- Browser default synthetic rebalanced scenario: total return **4.1986%**, ending value **10,419.86** from 10,000. Buy-and-hold scenario: total return **3.9457%**, ending value **10,394.57**. These are synthetic fixture results, not investment performance.
- Final formatted frontend reloaded and reported a successful 300-observation scenario.

## Independent review and regression fixes

- Reproduced a cancellation error in rebalanced portfolio growth for accepted extreme positive prices. A single asset priced `1e7 → 1e-9 → 1e7` incorrectly gained 11.0223%; `1e12 → 1e-9 → 1e12` was incorrectly rejected. Gross growth now uses direct price ratios, with regressions comparing every point against buy-and-hold. Both failures were observed before the fix and pass afterward.
- Reproduced source fingerprint changes from CLI newline normalization and browser UTF-8 byte-order-mark stripping. CLI and browser now preserve exact original UTF-8 CSV bytes. Regressions cover LF/CRLF/CR with and without a byte-order mark, constant canonical data hashes, and HTTP import. The affected tests failed before the fix and pass afterward.
- Independent rational-arithmetic oracle: 40 generated three-asset/eight-date scenarios in both portfolio modes, 80 comparisons total, maximum relative growth error `6.52e-16` on those fixtures. This is bounded numerical evidence, not an exhaustive precision guarantee.
- Rebuilt and reinstalled wheel after the fixes. From outside the checkout, the installed CLI preserved an original CRLF source hash, generated the 300-observation demo report, and supplied the new decoder asset. The installed server was restarted and Chrome reloaded the complete default scenario successfully.

## Not verified

The browser automation file chooser permission service could not grant a local upload. The attempt stopped at that control; it was not bypassed. CSV import was verified through the same local HTTP endpoint and through the CLI, but automated browser file selection plus submission was not completed. HTML/JSON/CSV export generation passed backend tests; browser download completion was not independently inspected.

The CI matrix is configured for Python 3.11 and 3.14 on Linux and Windows. Those hosted runs have not executed as part of this local record. Real provider feeds, market calendars, security master data, corporate actions, execution, advisory suitability and production hosting are outside this application.

The local HTTP server is a single-user desktop convenience, not an internet-facing deployment target. Concurrent requests are capped at four; uploaded data is processed in memory and never persisted by the server.


## Complete-workflow audit (2026-09-23)

- Fixed a valid-import workflow failure: disjoint asset dates previously prevented the asset controls from loading. Dataset inspection now validates the CSV before scenario analysis, so the user can deselect incompatible assets and retry. A successful new import clears the previous result; an invalid import preserves the previous dataset.
- Fixed destructive report failure behavior: forced writes previously truncated existing output before rendering. A same-directory temporary file is now published atomically after rendering and writing finish. Regressions verify preservation on rendering and replacement failure, and temporary-file cleanup.
- The updated suite passed **40 Python tests**, the two CSV decoder tests, JavaScript syntax checks and Ruff checks on Python 3.14/macOS. The newly added workflow and preservation regressions failed before their fixes.
- Rebuilt a wheel from the changed source and installed it without runtime dependencies into a fresh environment. From outside the checkout, four concurrent HTTP scenarios covered both modes and two starting values using unsorted BOM/CRLF data, extreme accepted positive prices, a constant asset, and a disjoint asset. Growth matched an independent rational-arithmetic calculation within `1e-14` relative tolerance. CLI and HTTP records matched exactly for identical settings.
- Reconstructed a fresh long-format input from each aligned CSV export and reran its recorded settings: all numerical series matched exactly. Aligned-only exports do not reconstruct excluded original observations or the original source fingerprint; retain the original CSV for full provenance.
- Two competing exclusive report writers produced one complete JSON report and one overwrite refusal.
- Chrome against the freshly installed server: default analysis completed; deselecting all assets showed an actionable error and retained the previous result; selecting one asset and buy-and-hold recovered; reloading the page restored the default synthetic scenario successfully.
- Browser file selection/import and completed browser downloads remain unverified because of the previously recorded upload-permission service limitation. The import recovery path was exercised through the local HTTP interface, not a browser file chooser. No permission denial was bypassed.

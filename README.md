# MarketObservatory

**Local analysis for price snapshots and portfolio allocations.**

Import a CSV snapshot, compare assets over shared dates, test portfolio weights under rebalancing or buy-and-hold, and export the inputs and results. The app runs on your computer with Python and a browser; the analysis engine uses the Python standard library.

[Synthetic example report](https://nazeeh111.github.io/MarketObservatory/) · Run the local app below to import data and compare scenarios.

## Start in one command

Requires Python **3.11 or later**. From this directory:

```sh
python3 -m market_observatory serve --open
```

Open `http://127.0.0.1:8765`. On Windows, use `py -3` instead of `python3` if appropriate. The included example contains **300 synthetic observations for four fictional assets**, including a designed drawdown interval. Its prices do not describe real securities.

Optional installation provides the `market-observatory` command:

```sh
python3 -m pip install .
market-observatory serve --open
```

Running from source needs no installation or network. Packaging uses setuptools at build time. Stop the server with Ctrl+C. A different local port can be selected with `--port 8873`.

## Analyze and export

1. Load the synthetic demo or expand **Import price CSV** and provide your local file and provenance.
2. Select assets and enter nonnegative relative weights. A valid import exposes all asset controls even if the initial selection has fewer than three common dates; deselect incompatible assets and run again. Weights normalize to 100%; unselected assets are excluded from date alignment.
3. Compare **rebalance each observation** with **buy and hold**, which allows allocations to drift. Set the observation frequency explicitly.
4. Inspect growth, peak-to-trough drawdown, annualized volatility, correlation, allocation drift, and data coverage. Use arrow keys on the growth chart to inspect dates.
5. Export a self-contained **HTML report**, complete **JSON** record, or aligned **CSV**. JSON retains every numerical series, settings, source metadata, and data fingerprints. Export reflects the last successful analysis; edited settings must be run first.

The engine never fills missing prices. All results share the exact intersection of selected asset dates. Coverage shows how many observations were excluded. Browser chart lines are sampled for large files; calculations and exports use all retained observations.

## Import contract

UTF-8 CSV with this exact header and one price per asset/date:

```csv
date,symbol,close
2024-01-02,ALPHA,100
2024-01-03,ALPHA,102
2024-01-04,ALPHA,101
2024-01-02,BETA,50
2024-01-03,BETA,49
2024-01-04,BETA,51
```

- Dates must be real `YYYY-MM-DD` calendar dates; timestamps/timezones are rejected rather than silently truncated.
- Symbols start with an uppercase letter, followed by uppercase letters, digits, `.`, `_`, or `-`; maximum 16 characters.
- Prices must be finite and between `1e-9` and `1e12`. Duplicate asset/date rows, missing fields, extra columns, and nonnumeric prices are rejected.
- Maximum 8 MiB, 100,000 rows, 16 assets and 20,000 common dates; at least three common dates are required.
- Supply a title, source, source **as-of date**, and price basis. Observation dates cannot be after the as-of date. The as-of date is supplied by you, not independently verified.
- Use comparable currency/valuation units and document adjustments in the notes. Splits and dividends are represented only if your supplied prices include them. Importing a file does not confer redistribution rights to its contents.

CSV rows may be unsorted. UTF-8 byte-order marks and LF, CRLF, or CR line endings are preserved in the source fingerprint. The report includes both the original CSV SHA-256 and a canonical data SHA-256 invariant to row order and equivalent numeric formatting. The app does not save uploaded files; retain your source snapshot and exports if you need a durable research record.

## Headless reports

```sh
python3 -m market_observatory report --output demo.html
python3 -m market_observatory report --format json --output demo.json \
  --mode buy_hold --symbols AURORA,HARBOR --weights AURORA=60,HARBOR=40
python3 -m market_observatory report --csv prices.csv --metadata source.json \
  --format csv --output aligned.csv --periods-per-year 12
```

`source.json`:

```json
{
  "title": "Monthly price snapshot",
  "source": "Your named data source and export procedure",
  "as_of": "2025-01-31",
  "price_basis": "adjusted",
  "notes": "Currency, adjustments, known gaps, and source limitations"
}
```

Existing output files are refused unless `--force` is supplied. Reports are fully rendered and written to a temporary file before atomic publication, so a failed render or replacement preserves an existing report. HTML reports are portable and contain no scripts or external assets. CSV exports contain all aligned prices, returns, growth and drawdowns; JSON is the full reproduction record.

## What the calculations mean

- **Simple return:** `P[t] / P[t-1] - 1`.
- **Growth:** each price divided by its first aligned price.
- **Drawdown:** value divided by the running maximum, minus one. Maximum drawdown is the minimum of this series, represented as a negative percentage.
- **Annualized volatility:** sample standard deviation of simple returns times the square root of periods per year. Default 252 assumes daily trading observations. This assumption is explicit, not inferred from dates.
- **CAGR:** `(last / first) ** (365.25 / elapsed_calendar_days) - 1`. Very short samples produce unstable extrapolations; unrepresentable extremes are `null` rather than infinity.
- **Correlation:** sample Pearson correlation of aligned simple returns. Constant series produce `null`, displayed as undefined.
- **Rebalanced portfolio:** multiply wealth each period by the weighted average gross return, restoring target weights after each observation.
- **Buy and hold:** initial weights times each asset's growth; end weights show the resulting drift.

Zero-weight assets still participate in comparisons and date alignment. Results describe historical scenarios; they are not forecasts or recommendations. The app does not model trading, leverage, cash yield, fees, taxes, slippage, or corporate actions independently of the supplied prices.

## Verification and architecture

```sh
python3 -m unittest discover -s tests -v
node --check market_observatory/static/app.js
node --test tests/browser_csv.test.cjs
```

Tests cover analytical two-asset examples, normalized weights, buy-and-hold vs rebalancing, alignment, undefined correlation, invalid numbers/dates/schema/settings, provenance hashes, escaped reports, overwrite protection and local HTTP boundaries. Node is only needed for the JavaScript development checks.

`engine.py` owns validation and math, `delivery.py` owns portable reports, `server.py` owns the loopback API, and `static/` owns presentation. The browser and CLI call the same engine. HTTP requests are bounded, accept only the local origin with a per-process request token, and cannot choose filesystem paths. Uploaded files stay in memory and are processed locally. The interface uses bundled assets and has no telemetry.

A portable [synthetic example report](docs/example-report.html) is included. Regenerate the CSV fixture with `python3 scripts/generate_demo.py /path/to/new-demo.csv`; existing destinations are refused.

See [design](docs/design.md), [verification](docs/verification.md), and [contributing](CONTRIBUTING.md). Original application code and synthetic fixture: MIT, copyright `nazeeh111`.

# MarketObservatory design

MarketObservatory imports price series from CSV, applies portfolio weights under selected assumptions, and exports analysis results with their source details. Python 3.11+ standard library supplies validation, analytics, the local HTTP service, and exports. The bundled HTML/CSS/JavaScript dashboard uses local assets and has no telemetry or runtime dependencies.

## Data contract

Long CSV: `date,symbol,close`, ISO calendar dates, uppercase ticker-like symbols and finite positive numeric prices. Reject duplicates, malformed schemas, missing fields, invalid dates, oversized datasets, and extreme numeric values. Metadata: title, source, as-of date, price basis, notes. Preserve raw SHA-256 and a canonical sorted data hash. Clearly label the bundled deterministic synthetic dataset. Never infer that imported data is live, adjusted or licensed for redistribution.

## Analysis

Select at most 16 assets for comparisons. Intersect dates across those assets; never forward-fill or silently impute. Show retained/dropped observations per asset. Simple period returns, cumulative growth, underwater drawdown, sample volatility, actual-calendar CAGR, sample correlation. Annualized volatility uses a user-visible periods-per-year assumption (default 252); sparse dates do not become daily observations. No Sharpe ratio without a defensible risk-free series.

Portfolio: nonnegative normalized weights, with explicit constant-weight rebalancing each observation or buy-and-hold mode. Include starting value, equity, realized allocation drift and return statistics. No fees, taxes, slippage, dividends beyond supplied adjusted prices, leverage, predictive claims or advice. No random price simulations presented as measured outcomes.

## Interface and exports

The dashboard shows dataset provenance beside controls for CSV import, asset selection, weights, annualization periods, and portfolio model. SVG charts display growth and drawdown; tables show returns, correlations, and date coverage. Exports include a self-contained HTML report, aligned CSV, and JSON record with the model settings and source fingerprints.

## Implementation and verification

1. Write numerical and invalid-input tests, observe failures, implement engine.
2. Add CLI and local HTTP app, test routes, request boundaries, CSRF, exports.
3. Build bundled UI, run syntax check and headless browser checks if available.
4. Document methods and limits, run complete tests, CLI demo/export and wheel installation/startup.

The app is served only on loopback with allowed Host checks, same-origin POST validation, a per-process token and bounded request body. It does not open files based on request URLs or save uploads. CLI outputs require explicit output path and refuse existing files unless --force.

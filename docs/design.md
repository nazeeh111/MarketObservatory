# MarketObservatory design

An original offline research terminal for comparing price series and explicit portfolio assumptions. Python 3.11+ standard library supplies validation, analytics, HTTP service and exports. Bundled HTML/CSS/JavaScript provides a responsive dashboard. No cloud accounts, market feeds, telemetry, trading, or runtime dependencies.

## Data contract

Long CSV: `date,symbol,close`, ISO calendar dates, uppercase ticker-like symbols and finite positive numeric prices. Reject duplicates, malformed schemas, missing fields, invalid dates, oversized datasets, and extreme numeric values. Metadata: title, source, as-of date, price basis, notes. Preserve raw SHA-256 and a canonical sorted data hash. Clearly label the bundled deterministic synthetic dataset. Never infer that imported data is live, adjusted or licensed for redistribution.

## Analysis

Select at most 16 assets for comparisons. Intersect dates across those assets; never forward-fill or silently impute. Show retained/dropped observations per asset. Simple period returns, cumulative growth, underwater drawdown, sample volatility, actual-calendar CAGR, sample correlation. Annualized volatility uses a user-visible periods-per-year assumption (default 252); sparse dates do not become daily observations. No Sharpe ratio without a defensible risk-free series.

Portfolio: nonnegative normalized weights, with explicit constant-weight rebalancing each observation or buy-and-hold mode. Include starting value, equity, realized allocation drift and return statistics. No fees, taxes, slippage, dividends beyond supplied adjusted prices, leverage, predictive claims or advice. No random price simulations presented as measured outcomes.

## Interface and exports

Dark navy research terminal, amber/cyan accents, labeled controls and charts, readable tables, keyboard focus. Source panel always visible. CSV import, asset checklist, weights, periods/year and scenario controls. SVG growth/drawdown charts; correlation matrix; metrics and data coverage tables. Export full JSON with model/provenance/version, aligned period CSV, and self-contained escaped HTML report.

## Implementation and verification

1. Write numerical and invalid-input tests, observe failures, implement engine.
2. Add CLI and local HTTP app, test routes, request boundaries, CSRF, exports.
3. Build bundled UI, run syntax check and headless browser checks if available.
4. Document methods and limits, run complete tests, CLI demo/export and wheel installation/startup.

The app is served only on loopback with allowed Host checks, same-origin POST validation, a per-process token and bounded request body. It does not open files based on request URLs or save uploads. CLI outputs require explicit output path and refuse existing files unless --force.

"use strict";
const $ = (id) => document.getElementById(id);
const palette = [
  "#57d3d5",
  "#a6b5fc",
  "#e890bc",
  "#86c997",
  "#b5a0dc",
  "#78b4e8",
  "#e6a17f",
  "#bbcc73",
];
let dataset = { demo: true },
  current = null,
  busy = false;
const pct = (value) =>
  value === null ? "Undefined" : `${(value * 100).toFixed(2)}%`;
const numeric = (value) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function error(message) {
  $("error").textContent = message;
  $("error").hidden = !message;
}
function setBusy(value) {
  busy = value;
  document
    .querySelectorAll("button, input, select, textarea")
    .forEach((button) => {
      button.disabled = value;
    });
  $("status").textContent = value ? "Calculating from local observations…" : "";
}
function table(headers, rows, classForRow = () => "") {
  const result = element("table"),
    head = element("thead"),
    body = element("tbody"),
    tr = element("tr");
  headers.forEach((label) => {
    const th = element("th", label);
    th.scope = "col";
    tr.append(th);
  });
  head.append(tr);
  result.append(head, body);
  rows.forEach((row, index) => {
    const line = element("tr", undefined, classForRow(index));
    row.forEach((value, i) => {
      const cell = element(i === 0 ? "th" : "td", value);
      if (i === 0) cell.scope = "row";
      line.append(cell);
    });
    body.append(line);
  });
  return result;
}
function controls(symbols) {
  const root = $("asset-controls");
  root.replaceChildren();
  symbols.forEach((symbol) => {
    const row = element("div", undefined, "asset-control");
    const label = element("label"),
      check = element("input");
    check.type = "checkbox";
    check.checked = true;
    check.dataset.symbol = symbol;
    label.append(check, document.createTextNode(symbol));
    const weight = element("input");
    weight.type = "number";
    weight.min = "0";
    weight.max = "1000000000";
    weight.step = "any";
    weight.value = "1";
    weight.setAttribute("aria-label", `${symbol} relative weight`);
    weight.dataset.weight = symbol;
    row.append(label, weight);
    root.append(row);
  });
}
function settings() {
  const symbols = [...document.querySelectorAll("[data-symbol]:checked")].map(
    (el) => el.dataset.symbol,
  );
  const weights = Object.fromEntries(
    symbols.map((symbol) => [
      symbol,
      Number(
        [...document.querySelectorAll("[data-weight]")].find(
          (el) => el.dataset.weight === symbol,
        ).value,
      ),
    ]),
  );
  return {
    symbols,
    weights,
    mode: $("mode").value,
    periods_per_year: Number($("periods").value),
    initial_value: Number($("initial").value),
  };
}
async function loadDataset(candidate) {
  if (busy) return;
  error("");
  setBusy(true);
  try {
    const response = await fetch("/api/inspect", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Research-Token": document.querySelector('meta[name="research-token"]').content,
      },
      body: JSON.stringify(candidate),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Import failed.");
    dataset = candidate;
    current = null;
    controls(payload.symbols);
    $("results").hidden = true;
    $("data-badge").textContent = "DATASET LOADED";
    $("subtitle").textContent = `${payload.metadata.title} · ${payload.symbols.length} assets loaded. Select assets and run a scenario.`;
  } catch (problem) {
    error(problem.message);
    setBusy(false);
    $("status").textContent = current
      ? "Import failed. Previous dataset and analysis remain available."
      : "Import failed. Select a valid CSV or load the demo.";
    return;
  }
  setBusy(false);
  await run(dataset);
}
async function run(candidate) {
  if (busy) return;
  error("");
  setBusy(true);
  try {
    const body = {
      ...candidate,
      settings: settings(),
    };
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Research-Token": document.querySelector(
          'meta[name="research-token"]',
        ).content,
      },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Analysis failed.");
    dataset = candidate;
    current = payload;
    render(payload.result);
    $("status").textContent =
      `Analysis complete · ${payload.result.dates.length} shared observations · ${payload.result.settings.mode === "buy_hold" ? "buy and hold" : "rebalanced each observation"}`;
  } catch (problem) {
    error(problem.message);
    $("status").textContent = current
      ? "Previous successful analysis remains displayed. Changes were not applied."
      : "Dataset loaded. Adjust the selected assets or settings and run the scenario again.";
  } finally {
    busy = false;
    document
      .querySelectorAll("button, input, select, textarea")
      .forEach((button) => {
        button.disabled = false;
      });
  }
}
function svgElement(tag, attributes = {}, text) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attributes).forEach(([key, value]) =>
    node.setAttribute(key, String(value)),
  );
  if (text !== undefined) node.textContent = text;
  return node;
}
function chart(target, series, dates, percent = false, interactive = false) {
  const width = 900,
    height = percent ? 250 : 310,
    left = 62,
    right = 24,
    top = 22,
    bottom = 37;
  const plotW = width - left - right,
    plotH = height - top - bottom;
  let low = Infinity,
    high = -Infinity;
  series.forEach((s) =>
    s.values.forEach((value) => {
      low = Math.min(low, value);
      high = Math.max(high, value);
    }),
  );
  const pad = (high - low) * 0.12 || 0.01;
  low -= pad;
  high += pad;
  const x = (i) => left + (i * plotW) / (dates.length - 1),
    y = (value) => top + ((high - value) * plotH) / (high - low);
  const svg = svgElement("svg", {
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": `${percent ? "Portfolio drawdown" : "Growth of 100"} from ${dates[0]} to ${dates.at(-1)}. Full values are available in the aligned CSV export.`,
  });
  for (let tick = 0; tick < 5; tick++) {
    const value = low + ((high - low) * tick) / 4,
      py = y(value);
    svg.append(
      svgElement("line", {
        x1: left,
        x2: width - right,
        y1: py,
        y2: py,
        stroke: "#29394c",
        "stroke-dasharray": "3 5",
      }),
      svgElement(
        "text",
        {
          x: left - 10,
          y: py + 4,
          "text-anchor": "end",
          fill: "#91a4bd",
          "font-size": 11,
          "font-family": "monospace",
        },
        percent ? `${(value * 100).toFixed(0)}%` : numeric(value),
      ),
    );
  }
  const stride = Math.max(1, Math.ceil(dates.length / 1200));
  const indices = [
    ...new Set([
      ...Array.from(
        { length: Math.ceil(dates.length / stride) },
        (_, i) => i * stride,
      ),
      dates.length - 1,
    ]),
  ];
  series.forEach((s) => {
    const d = indices
      .map(
        (i, j) =>
          `${j ? "L" : "M"}${x(i).toFixed(2)},${y(s.values[i]).toFixed(2)}`,
      )
      .join(" ");
    svg.append(
      svgElement("path", {
        d,
        fill: "none",
        stroke: s.color,
        "stroke-width": s.name === "Portfolio" ? 3 : 1.65,
        "stroke-linejoin": "round",
        "stroke-linecap": "round",
      }),
    );
  });
  [0, Math.floor((dates.length - 1) / 2), dates.length - 1].forEach((i, n) =>
    svg.append(
      svgElement(
        "text",
        {
          x: x(i),
          y: height - 8,
          "text-anchor": n === 0 ? "start" : n === 2 ? "end" : "middle",
          fill: "#91a4bd",
          "font-size": 11,
          "font-family": "monospace",
        },
        dates[i],
      ),
    ),
  );
  if (interactive) {
    svg.setAttribute("tabindex", "0");
    svg.setAttribute(
      "aria-label",
      svg.getAttribute("aria-label") +
        " Use left and right arrow keys to inspect observations.",
    );
    let selected = dates.length - 1;
    const cursor = svgElement("line", {
      x1: x(selected),
      x2: x(selected),
      y1: top,
      y2: height - bottom,
      stroke: "#8093ad",
      "stroke-dasharray": "3 4",
    });
    svg.append(cursor);
    const inspect = (i) => {
      selected = Math.max(0, Math.min(dates.length - 1, i));
      cursor.setAttribute("x1", x(selected));
      cursor.setAttribute("x2", x(selected));
      $("chart-readout").textContent =
        `${dates[selected]}  |  ` +
        series
          .map((s) => `${s.name}: ${numeric(s.values[selected])}`)
          .join(" · ");
    };
    svg.addEventListener("pointermove", (event) => {
      const rect = svg.getBoundingClientRect();
      inspect(
        Math.round(
          ((((event.clientX - rect.left) / rect.width) * width - left) /
            plotW) *
            (dates.length - 1),
        ),
      );
    });
    svg.addEventListener("keydown", (event) => {
      if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        inspect(
          event.key === "Home"
            ? 0
            : event.key === "End"
              ? dates.length - 1
              : selected + (event.key === "ArrowRight" ? 1 : -1),
        );
      }
    });
    inspect(selected);
  }
  $(target).replaceChildren(svg);
}
function render(result) {
  $("results").hidden = false;
  $("dataset-name").textContent = result.metadata.title;
  $("dataset-source").textContent = result.metadata.source;
  $("dataset-asof").textContent = result.metadata.as_of;
  $("dataset-basis").textContent = `${result.metadata.price_basis} prices`;
  $("date-window").textContent = `${result.dates[0]} → ${result.dates.at(-1)}`;
  $("observation-count").textContent =
    `${result.dates.length} observations · ${result.assets.length} assets`;
  $("data-badge").textContent =
    result.metadata.price_basis === "synthetic"
      ? "SYNTHETIC DATA"
      : "LOCAL SNAPSHOT";
  $("subtitle").textContent =
    result.metadata.price_basis === "synthetic"
      ? "Four fictional assets. Real calculations. No live market data."
      : "Your imported snapshot, analyzed locally with explicit assumptions.";
  const metrics = [
    ["Total return", result.portfolio.total_return, "Entire aligned window"],
    [
      "Annualized volatility",
      result.portfolio.annualized_volatility,
      `${result.settings.periods_per_year} periods / year`,
    ],
    [
      "Maximum drawdown",
      result.portfolio.max_drawdown,
      "Largest peak-to-trough loss",
    ],
    [
      "Ending value",
      result.series.portfolio_value.at(-1),
      `Started at ${numeric(result.settings.initial_value)} · input units`,
    ],
  ];
  $("metrics").replaceChildren(
    ...metrics.map(([label, value, detail], index) => {
      const card = element("div", undefined, "metric");
      card.append(
        element("div", label, "metric-label"),
        element(
          "div",
          index === 3 ? numeric(value) : pct(value),
          "metric-value " +
            (index === 0
              ? value >= 0
                ? "positive"
                : "negative"
              : index === 2
                ? "negative"
                : ""),
        ),
        element("div", detail, "metric-detail"),
      );
      return card;
    }),
  );
  const series = result.settings.symbols.map((symbol, i) => ({
    name: symbol,
    values: result.series.growth[symbol].map((x) => 100 * x),
    color: palette[i % palette.length],
  }));
  series.push({
    name: "Portfolio",
    values: result.series.portfolio_growth.map((x) => 100 * x),
    color: "#f5bd60",
  });
  $("legend").replaceChildren(
    ...series.map((s) => {
      const item = element("span");
      const mark = svgElement("svg", {
        width: 10,
        height: 6,
        "aria-hidden": "true",
      });
      mark.append(
        svgElement("path", {
          d: "M0,3 L10,3",
          stroke: s.color,
          "stroke-width": 3,
        }),
      );
      item.append(mark, document.createTextNode(s.name));
      return item;
    }),
  );
  chart("growth-chart", series, result.dates, false, true);
  chart(
    "drawdown-chart",
    [
      {
        name: "Portfolio",
        values: result.series.portfolio_drawdown,
        color: "#f6a18c",
      },
    ],
    result.dates,
    true,
  );
  $("correlation").replaceChildren(
    table(
      ["", ...result.settings.symbols],
      result.correlation.map((row, i) => [
        result.settings.symbols[i],
        ...row.map((value) => (value === null ? "—" : value.toFixed(2))),
      ]),
    ),
  );
  const rows = [
    [
      "Portfolio",
      ...["total_return", "cagr", "annualized_volatility", "max_drawdown"].map(
        (key) => pct(result.portfolio[key]),
      ),
      "100.00%",
      "100.00%",
    ],
    ...result.assets.map((a) => [
      a.symbol,
      ...["total_return", "cagr", "annualized_volatility", "max_drawdown"].map(
        (key) => pct(a[key]),
      ),
      pct(result.settings.weights[a.symbol]),
      pct(result.portfolio.terminal_weights[a.symbol]),
    ]),
  ];
  $("asset-table").replaceChildren(
    table(
      [
        "Series",
        "Return",
        "CAGR",
        "Annual vol.",
        "Max drawdown",
        "Start weight",
        "End weight",
      ],
      rows,
      (i) => (i === 0 ? "portfolio-row" : ""),
    ),
  );
  $("coverage").replaceChildren(
    table(
      ["Asset", "Available", "Retained", "Excluded"],
      result.coverage.map((row) => [
        row.symbol,
        row.available,
        row.retained,
        row.excluded,
      ]),
    ),
  );
  $("dataset-notes").textContent =
    result.metadata.notes || "No additional source notes.";
  $("provenance").textContent =
    `Canonical data SHA-256\n${result.provenance.data_sha256}\n\nOriginal CSV SHA-256\n${result.provenance.source_sha256}\n\nEngine ${result.engine_version} · schema ${result.schema_version}\nLongest shared-date gap: ${result.max_calendar_gap_days} calendar days`;
  $("warnings").replaceChildren(
    ...result.warnings.map((w) => element("li", w)),
  );
}
$("demo").addEventListener("click", () => loadDataset({ demo: true }));
$("scenario").addEventListener("submit", (event) => {
  event.preventDefault();
  run(dataset);
});
$("scenario").addEventListener("input", () => {
  if (current && !busy)
    $("status").textContent =
      "Scenario settings changed. Run scenario to update the displayed results and exports.";
});
$("import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = $("file").files[0];
  if (!file) return;
  if (file.size > 8 * 1024 * 1024) {
    error("CSV must be at most 8 MiB.");
    return;
  }
  try {
    const bytes = await file.arrayBuffer();
    const text = decodeCsvBytes(bytes);
    await loadDataset(
      {
        csv: text,
        metadata: {
          title: $("title").value,
          source: $("source").value,
          as_of: $("as-of").value,
          price_basis: $("basis").value,
          notes: $("notes").value,
        },
      },
    );
  } catch (problem) {
    error(`Could not read UTF-8 CSV: ${problem.message}`);
  }
});
document.querySelectorAll("[data-export]").forEach((button) =>
  button.addEventListener("click", () => {
    if (!current) return;
    const type = button.dataset.export;
    const data =
      type === "json"
        ? JSON.stringify(current.result, null, 2)
        : current.exports[type];
    const mime = {
      html: "text/html",
      csv: "text/csv",
      json: "application/json",
    }[type];
    const url = URL.createObjectURL(
      new Blob([data], { type: `${mime};charset=utf-8` }),
    );
    const link = element("a");
    link.href = url;
    link.download = `market-observatory-${current.result.provenance.data_sha256.slice(0, 8)}.${type}`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }),
);
loadDataset({ demo: true });

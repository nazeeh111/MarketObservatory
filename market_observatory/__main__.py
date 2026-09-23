"""Command-line dashboard and reproducible report entry points."""

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from .delivery import demo_dataset, write_report
from .engine import MAX_BYTES, ValidationError, analyze, parse_csv
from .server import create_server


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="MarketObservatory: offline price research and portfolio scenarios"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Start the local dashboard")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--open", action="store_true", help="Open the local URL in a browser")
    report = sub.add_parser("report", help="Export a headless research report")
    report.add_argument("--csv", type=Path, help="Long-format CSV; omit for synthetic demo")
    report.add_argument("--metadata", type=Path, help="JSON provenance; required with --csv")
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--format", choices=["json", "csv", "html"], default="html")
    report.add_argument("--symbols", help="Comma-separated asset selection")
    report.add_argument("--weights", help="Comma-separated SYMBOL=WEIGHT values")
    report.add_argument("--mode", choices=["rebalance", "buy_hold"], default="rebalance")
    report.add_argument("--periods-per-year", type=float, default=252)
    report.add_argument("--initial-value", type=float, default=10000)
    report.add_argument("--force", action="store_true", help="Replace an existing report file")
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            if not 0 <= args.port <= 65535:
                raise ValidationError("Port must be between 0 and 65535.")
            server = create_server(args.port)
            url = f"http://127.0.0.1:{server.server_port}"
            print(
                f"MarketObservatory: {url}\nLocal only. Press Ctrl+C to stop.",
                flush=True,
            )
            if args.open:
                webbrowser.open(url)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        else:
            if bool(args.csv) != bool(args.metadata):
                raise ValidationError("--csv and --metadata must be supplied together.")
            if args.csv:
                if args.csv.stat().st_size > MAX_BYTES or args.metadata.stat().st_size > 65536:
                    raise ValidationError("CSV or metadata file exceeds the size limit.")
                dataset = parse_csv(
                    args.csv.read_bytes().decode("utf-8"),
                    json.loads(args.metadata.read_text(encoding="utf-8")),
                )
            else:
                dataset = demo_dataset()
            weights = None
            if args.weights:
                pairs = [x.split("=") for x in args.weights.split(",")]
                if any(len(x) != 2 for x in pairs) or len({x[0] for x in pairs}) != len(pairs):
                    raise ValidationError("Weights must be unique SYMBOL=WEIGHT pairs.")
                weights = dict(pairs)
            result = analyze(
                dataset,
                symbols=args.symbols.split(",") if args.symbols else None,
                weights=weights,
                mode=args.mode,
                periods_per_year=args.periods_per_year,
                initial_value=args.initial_value,
            )
            write_report(result, args.output, args.format, args.force)
            print(
                f"Wrote {args.output} | {len(result['dates'])} aligned observations | SHA-256 {result['provenance']['data_sha256']}"
            )
        return 0
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

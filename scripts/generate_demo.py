"""Regenerate the synthetic CSV into an explicit destination; never market data."""

import argparse
import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path


def generate(destination):
    rng = random.Random(20260923)
    prices = {"AURORA": 100.0, "CIRRUS": 100.0, "HARBOR": 100.0, "TERRA": 100.0}
    day = date(2024, 1, 2)
    with Path(destination).open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "symbol", "close"])
        for i in range(300):
            while day.weekday() > 4:
                day += timedelta(days=1)
            common = rng.gauss(0, 0.008)
            returns = {
                "AURORA": 0.0005 + common + rng.gauss(0, 0.006),
                "CIRRUS": 0.0002 - 0.25 * common + rng.gauss(0, 0.003),
                "HARBOR": 0.0001 + rng.gauss(0, 0.0015),
                "TERRA": 0.0003 + 0.5 * common + rng.gauss(0, 0.007),
            }
            if 105 <= i < 120:
                returns["AURORA"] -= 0.009
                returns["TERRA"] -= 0.006
            for symbol, price in prices.items():
                prices[symbol] = price * math.exp(returns[symbol])
                writer.writerow([day.isoformat(), symbol, f"{prices[symbol]:.6f}"])
            day += timedelta(days=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    generate(parser.parse_args().output)

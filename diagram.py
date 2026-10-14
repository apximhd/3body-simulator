"""Plot a histogram of delta_e from a Statistic-mode CSV export."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import sys

import matplotlib.pyplot as plt


def read_delta_e(path: Path) -> tuple[list[float], int]:
    values: list[float] = []
    skipped = 0
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "delta_e" not in reader.fieldnames:
            raise ValueError("CSV must contain a 'delta_e' column")
        for row in reader:
            raw = row.get("delta_e")
            if raw is None or not raw.strip():
                skipped += 1
                continue
            try:
                value = float(raw)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid delta_e at CSV line {reader.line_num}: {raw!r}"
                ) from exc
            if not math.isfinite(value):
                skipped += 1
                continue
            values.append(value)
    if not values:
        raise ValueError("CSV contains no finite delta_e values")
    return values, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path, help="Statistic-mode CSV file")
    parser.add_argument(
        "--bins", type=int, default=50,
        help="Number of histogram bins (default: 50)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Save the histogram to an image instead of opening a window",
    )
    args = parser.parse_args()
    if args.bins <= 0:
        parser.error("--bins must be a positive integer")

    try:
        values, skipped = read_delta_e(args.csv_file)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        parser.error(str(exc))
    if skipped:
        print(
            f"Warning: skipped {skipped} empty or non-finite delta_e value(s)",
            file=sys.stderr,
        )

    plt.rcParams["savefig.format"] = "pdf"
    fig, ax = plt.subplots()
    ax.hist(values, bins=args.bins, edgecolor="black")
    ax.set_xlabel("delta_e")
    ax.set_ylabel("Count")
    ax.set_title(f"delta_e histogram (N={len(values)})")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    if args.output:
        try:
            fig.savefig(args.output)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        finally:
            plt.close(fig)
    else:
        plt.show()


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
import itertools
import math
import multiprocessing as mp
import os
import re
import sys
import tempfile
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path

import numpy as np

from core.batch import default_max_workers, run_stat_task


TARGET_COLUMNS = ("Δe_in", "σ", "SE")
RESULT_COLUMNS = (
    "Imax", "Imin", "R", "delta_e", "delta_e_out",
    "e_out_last", "a_out_last", "a_in_ratio", "stability_status",
)
FILENAME_PARAMS = (
    ("M_1", "M1"),
    ("M_2", "M2"),
    ("M_3", "M3"),
    ("a_in", "aAB"),
    ("e_in", "eAB"),
    ("i_in", "iAB"),
    ("Ω_in", "OmAB"),
    ("ω_in", "omAB"),
    ("M_in", "MAB"),
    ("Q", "Q"),
    ("e_out", "eAC"),
    ("i_out", "iAC"),
    ("Ω_out", "OmAC"),
    ("ω_out", "omAC"),
    ("M_out", "MAC"),
)
CSV_TO_PARAM = {
    "M_1": "mass_A",
    "M_2": "mass_B",
    "M_3": "mass_C",
    "a_in": "a_AB",
    "e_in": "e_AB",
    "i_in": "i_AB",
    "Ω_in": "Omega_AB",
    "ω_in": "omega_AB",
    "M_in": "M_AB",
    "Q": "Q",
    "e_out": "e_AC",
    "i_out": "i_AC",
    "Ω_out": "Omega_AC",
    "ω_out": "omega_AC",
    "M_out": "M_AC",
}
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
RANGE_PATTERN = re.compile(rf"^\s*({NUMBER})-({NUMBER})-({NUMBER})\s*$")
PARAMETER_COLUMNS = tuple(CSV_TO_PARAM.values()) + (
    "t_max", "t_delay", "t_AC",
)


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _values_from_cell(value: str, column: str) -> list[float]:
    text = (value or "").strip()
    match = RANGE_PATTERN.fullmatch(text)
    if match:
        start, end, step = map(float, match.groups())
        if step == 0 or start == end:
            return [start]
        count = int(round(abs(end - start) / abs(step))) + 1
        values = start + np.arange(max(1, count)) * step
        tolerance = abs(step) * 1e-9
        if step > 0:
            values = values[values <= end + tolerance]
            if values.size and values[-1] < end - tolerance:
                values = np.append(values, end)
        else:
            values = values[values >= end - tolerance]
            if values.size and values[-1] > end + tolerance:
                values = np.append(values, end)
        return [float(item) for item in values] or [start]
    try:
        return [float(text)]
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value in column {column!r}: {value!r}") from exc


def _statistic_filename(row: dict[str, str]) -> str:
    parts = []
    for column, name in FILENAME_PARAMS:
        value = row[column]
        values = _values_from_cell(value, column)
        if RANGE_PATTERN.fullmatch(value.strip()):
            step = values[1] - values[0] if len(values) > 1 else 0.0
            value_text = "-".join(
                (f"{values[0]:g}", f"{values[-1]:g}", f"{step:g}")
            )
        else:
            value_text = f"{values[0]:g}"
        parts.append(f"{name}={value_text}")
    return "_".join(parts) + ".csv"


def _parameter_sets(row: dict[str, str], fieldnames: list[str]):
    range_columns = [column for column in CSV_TO_PARAM if column in fieldnames]
    values = {
        column: _values_from_cell(row.get(column) or "", column)
        for column in range_columns
    }
    t_max = float(row["T_max"])
    t_delay = float(row["Extra_time"])
    total = math.prod(len(column_values) for column_values in values.values())

    def generate():
        columns = list(values)
        for combination in itertools.product(*(values[column] for column in columns)):
            params = {
                CSV_TO_PARAM[column]: value
                for column, value in zip(columns, combination)
            }
            params["t_max"] = t_max
            params["t_delay"] = t_delay
            params["t_AC"] = 0.0
            yield params

    return generate(), total


def _format_result_row(
    row: dict, fieldnames: list[str], scanned_columns: list[str]
) -> dict[str, str]:
    formatted = {}
    for column_index, column in enumerate(fieldnames):
        value = row.get(column, "")
        if value is None:
            formatted[column] = ""
        elif column == "stability_status":
            formatted[column] = str(value)
        elif column in RESULT_COLUMNS:
            try:
                number = float(value)
            except (TypeError, ValueError):
                formatted[column] = str(value)
            else:
                precision = 5 if column == "a_in_ratio" else 8
                formatted[column] = f"{number:.{precision}f}"
        elif column in scanned_columns:
            try:
                number = float(value)
            except (TypeError, ValueError):
                formatted[column] = str(value)
            else:
                precision = (
                    3 if column_index < 2
                    and column in {"e_AB", "e_AC", "a_AB", "Q"}
                    else 1
                )
                formatted[column] = f"{number:.{precision}f}"
        elif isinstance(value, (int, float, np.number)):
            formatted[column] = format(float(value), ".17g")
        else:
            formatted[column] = str(value)
    return formatted


def _calculate_row(row: dict[str, str], row_number: int, row_count: int,
                   fieldnames: list[str], workers: int,
                   result_fieldnames: list[str]) -> tuple[list[float], list[dict]]:
    params_iter, total = _parameter_sets(row, fieldnames)
    worker_count = min(workers, total)
    max_in_flight = max(1, worker_count * 2)
    context = mp.get_context("spawn")
    pending = {}
    results: list[float] = []
    result_rows_by_index: dict[int, dict] = {}
    scanned_columns = result_fieldnames[:-len(RESULT_COLUMNS)]
    completed = 0
    last_percent = 0
    bar_width = 50
    row_started_at = time.monotonic()
    next_index = 0
    exhausted = False

    sys.stdout.write(
        f"\r[{row_number}/{row_count}] "
        f"[{' ' * bar_width}]   0% | 0/{total} | 0:00 elapsed"
    )
    sys.stdout.flush()

    with ProcessPoolExecutor(
        max_workers=worker_count,
        mp_context=context,
    ) as executor:
        while pending or not exhausted:
            while len(pending) < max_in_flight and not exhausted:
                try:
                    params = next(params_iter)
                except StopIteration:
                    exhausted = True
                    break
                task = {
                    "params": params,
                    "scanned_keys": PARAMETER_COLUMNS,
                    "integrator": "IAS15",
                    "dt": 0.04,
                    "n_output": 5000,
                    "index": next_index,
                }
                future = executor.submit(run_stat_task, task)
                pending[future] = None
                next_index += 1

            if not pending:
                continue
            finished, _ = wait(
                pending, return_when=FIRST_COMPLETED
            )
            for future in finished:
                pending.pop(future)
                result = future.result()
                result_index = int(result.pop("_index", -1))
                result_rows_by_index[result_index] = _format_result_row(
                    result, result_fieldnames, scanned_columns
                )
                delta_e = result.get("delta_e")
                if (
                    result.get("success")
                    and not result.get("internal_breakup", False)
                    and delta_e is not None
                    and np.isfinite(delta_e)
                ):
                    results.append(float(delta_e))
                completed += 1
                percent = int(100.0 * completed / total)
                if percent == last_percent:
                    continue
                last_percent = percent
                filled_width = int(bar_width * percent / 100)
                progress_bar = (
                    f"[{'█' * filled_width}{' ' * (bar_width - filled_width)}]"
                )
                elapsed = time.monotonic() - row_started_at
                time_label = f"{_format_duration(elapsed)} elapsed"
                if completed < total:
                    remaining = elapsed * (total - completed) / completed
                    time_label += f" | ~{_format_duration(remaining)} left"
                sys.stdout.write(
                    f"\r[{row_number}/{row_count}] {progress_bar} {percent:3d}% | "
                    f"{completed}/{total} | {time_label}"
                )
                sys.stdout.flush()

    if total == 0:
        print(f"[{row_number}/{row_count}] no simulations")
    else:
        print()
    result_rows = [result_rows_by_index[index] for index in range(total)]
    return results, result_rows


def _save_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(
                {column: row.get(column) or "" for column in fieldnames}
                for row in rows
            )
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _append_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("a", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writerows(rows)
        output.flush()
        os.fsync(output.fileno())


def _process_file(path: Path, workers: int) -> int:
    with path.open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError("CSV has no header row")
        missing_columns = [
            column for column in (*TARGET_COLUMNS, *CSV_TO_PARAM, "T_max", "Extra_time")
            if column not in fieldnames
        ]
        if missing_columns:
            raise ValueError(
                "CSV is missing required columns: " + ", ".join(missing_columns)
            )
        rows = list(reader)

    pending_rows = [
        index for index, row in enumerate(rows)
        if any(not (row.get(column) or "").strip() for column in TARGET_COLUMNS)
    ]
    if not pending_rows:
        print("No rows with empty Δe_in, σ, or SE values.")
        return 0

    print(f"Processing {len(pending_rows)} of {len(rows)} row(s) with {workers} worker(s).")
    started_at = time.monotonic()
    result_paths = []
    for row_index in pending_rows:
        row = rows[row_index]
        scanned_columns = [
            CSV_TO_PARAM[column]
            for column in CSV_TO_PARAM
            if RANGE_PATTERN.fullmatch((row.get(column) or "").strip())
        ]
        result_fieldnames = scanned_columns + list(RESULT_COLUMNS)
        result_path = path.with_name(_statistic_filename(row))
        _save_csv(result_path, result_fieldnames, [])
        result_paths.append(result_path)
        results, result_rows = _calculate_row(
            row, row_index + 1, len(rows), fieldnames, workers,
            result_fieldnames,
        )
        _append_csv(result_path, result_fieldnames, result_rows)
        if results:
            mean = float(np.mean(results))
            sigma = float(np.std(results))
            standard_error = sigma / math.sqrt(len(results))
            calculated = (mean, sigma, standard_error)
            for column, value in zip(TARGET_COLUMNS, calculated):
                if not (row.get(column) or "").strip():
                    row[column] = format(value, ".6g")
        _save_csv(path, fieldnames, rows)

    elapsed = time.monotonic() - started_at
    print(f"Total {_format_duration(elapsed)} elapsed.")
    print(f"Saved {len(result_paths)} full results CSV file(s) in {path.parent}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fill missing Δe_in, σ, and SE values in a statistic CSV."
    )
    parser.add_argument("path", type=Path, help="Path to the statistic CSV file")
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Process count (default: automatic, like Statistic mode)",
    )
    args = parser.parse_args()
    if not args.path.is_file():
        parser.error(f"file not found: {args.path}")
    if args.workers < 0:
        parser.error("--workers must be zero (automatic) or a positive integer")

    try:
        return _process_file(args.path, default_max_workers(args.workers))
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())

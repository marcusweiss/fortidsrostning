#!/usr/bin/env python3
"""Hämtar förtidsröst-CSV från Valmyndigheten och skriver docs/data.json."""

from __future__ import annotations

import csv
import json
import sys
import urllib.request
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"
OUTPUT_PATH = ROOT / "docs" / "data.json"


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def fetch_csv(url: str) -> str:
    with urllib.request.urlopen(url, timeout=120) as response:
        raw = response.read()
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise RuntimeError("Kunde inte avkoda CSV-filen")


def normalize_date(value: str) -> str:
    return value.strip().split(" ", 1)[0]


def parse_2022_totals(text: str) -> tuple[list[str], dict[str, int]]:
    header = text.splitlines()[0]
    date_columns = [
        normalize_date(name)
        for name in header.split(";")
        if name.startswith("2022")
    ]
    summa_line = next(
        (line for line in text.splitlines() if ";SUMMA;" in line),
        None,
    )
    if not summa_line:
        raise RuntimeError("Ingen SUMMA-rad i 2022-filen")

    parts = summa_line.split(";")
    offset = 6
    daily = {
        date: int(parts[offset + index] or 0)
        for index, date in enumerate(date_columns)
    }
    return date_columns, daily


def parse_daily_totals(text: str, scale_factor: float = 1.0) -> tuple[list[str], dict[str, int]]:
    reader = csv.DictReader(StringIO(text), delimiter=";")
    if not reader.fieldnames:
        raise RuntimeError("CSV saknar kolumnrubriker")

    date_columns = [
        normalize_date(name)
        for name in reader.fieldnames
        if name and name[:4].isdigit()
    ]
    rows = list(reader)

    lokal_key = "LOKAL" if "LOKAL" in reader.fieldnames else "lokal"
    summary_rows = [
        row for row in rows if row.get(lokal_key, "").strip().upper() == "SUMMA"
    ]
    if summary_rows:
        summary = summary_rows[0]
        daily = {
            date: round(int(summary.get(date) or 0) * scale_factor)
            for date in date_columns
        }
        return date_columns, daily

    detail_rows = [
        row for row in rows if row.get(lokal_key, "").strip().upper() != "SUMMA"
    ]
    daily = {
        date: round(
            sum(int(row.get(date) or 0) for row in detail_rows) * scale_factor
        )
        for date in date_columns
    }
    return date_columns, daily


def build_series(
    date_columns: list[str],
    daily: dict[str, int],
    eligible_voters: int,
    reference_turnout: float,
) -> list[dict]:
    expected_voters = eligible_voters * reference_turnout
    cumulative = 0
    series: list[dict] = []

    for day_number, date in enumerate(date_columns, start=1):
        count = daily[date]
        cumulative += count
        series.append(
            {
                "day": day_number,
                "date": date,
                "daily": count,
                "cumulative": cumulative,
                "pct_eligible": round(100 * cumulative / eligible_voters, 3),
                "pct_expected_votes": round(
                    100 * cumulative / expected_voters, 3
                ),
            }
        )
    return series


def trim_series(series: list[dict]) -> list[dict]:
    last_index = -1
    for index, point in enumerate(series):
        if point["daily"] > 0:
            last_index = index
    if last_index >= 0:
        return series[: last_index + 1]
    return []


def main() -> int:
    config = load_config()
    reference_turnout = config["reference_turnout"]
    eligible_voters = config["eligible_voters_riksdag"]

    csv_text = fetch_csv(config["source_url"])
    date_columns, daily = parse_daily_totals(csv_text)
    series = build_series(date_columns, daily, eligible_voters, reference_turnout)
    active = trim_series(series)
    latest = active[-1] if active else None

    comparison: list[dict] = []
    for election in config.get("comparison_elections", []):
        election_text = fetch_csv(election["url"])
        if election["year"] == 2022:
            date_columns, daily = parse_2022_totals(election_text)
        else:
            date_columns, daily = parse_daily_totals(
                election_text, election.get("scale_factor", 1.0)
            )
        election_series = trim_series(
            build_series(
                date_columns,
                daily,
                election["eligible_voters"],
                reference_turnout,
            )
        )
        comparison.append(
            {
                "year": election["year"],
                "eligible_voters": election["eligible_voters"],
                "points": election_series,
            }
        )
    max_day = max(
        [len(active), *(len(item["points"]) for item in comparison)],
        default=0,
    )

    expected_voters = eligible_voters * reference_turnout

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": config["source_url"],
        "source_name": config["source_name"],
        "election_day": config["election_day"],
        "eligible_voters": eligible_voters,
        "reference_turnout_pct": round(reference_turnout * 100, 2),
        "expected_voters": round(expected_voters),
        "max_day": max_day,
        "latest": latest,
        "series": series,
        "comparison": comparison,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    if latest:
        print(
            f"Senaste: {latest['date']} – {latest['cumulative']:,} röster "
            f"({latest['pct_eligible']}% av röstberättigade, "
            f"{latest['pct_expected_votes']}% av förväntade röster)".replace(",", " ")
        )
    print(f"Skrev {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

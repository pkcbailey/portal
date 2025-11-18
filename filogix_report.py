#!/usr/bin/env python3

"""
Generate categorized DNS record report for filogix.com CSV exports.

Usage:
    ./filogix_report.py /path/to/filogix.com.csv
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List


@dataclass(frozen=True)
class Record:
    name: str
    type: str
    ttl: str
    rdata: str

    @property
    def type_upper(self) -> str:
        return self.type.upper()

    @property
    def name_lower(self) -> str:
        return self.name.lower()

    @property
    def rdata_lower(self) -> str:
        return self.rdata.lower()


def load_records(csv_path: Path) -> List[Record]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            Record(
                name=row["name"].strip(),
                type=row["type"].strip(),
                ttl=row["ttl"].strip(),
                rdata=row["rdata"].strip(),
            )
            for row in reader
        ]


def filter_caa_exceptions(records: Iterable[Record]) -> List[Record]:
    allow_keywords = ("sectigo", "digicert", "entrust")
    matches: List[Record] = []
    for record in records:
        if record.type_upper != "CAA":
            continue
        for chunk in (part.strip() for part in record.rdata.split(",")):
            lowered = chunk.lower()
            if "issue" not in lowered:
                continue
            if "issuewild" in lowered:
                continue
            if any(keyword in lowered for keyword in allow_keywords):
                continue
            matches.append(
                Record(
                    name=record.name,
                    type=record.type,
                    ttl=record.ttl,
                    rdata=chunk,
                )
            )
    return matches


def filter_email(records: Iterable[Record]) -> List[Record]:
    substrings = ("mail", "smtp")
    matches: List[Record] = []
    for record in records:
        if record.type_upper == "MX":
            matches.append(record)
            continue
        if any(sub in record.name_lower for sub in substrings):
            matches.append(record)
            continue
        if any(sub in record.rdata_lower for sub in substrings):
            matches.append(record)
    return matches


def filter_ftp(records: Iterable[Record]) -> List[Record]:
    matches: List[Record] = []
    for record in records:
        name_lower = record.name_lower
        if "ftp" not in name_lower:
            continue
        if "sftp" in name_lower or "secureftp" in name_lower:
            continue
        matches.append(record)
    return matches


def filter_ns(records: Iterable[Record]) -> List[Record]:
    return [record for record in records if record.type_upper == "NS"]


def filter_relay(records: Iterable[Record]) -> List[Record]:
    return [record for record in records if "relay" in record.name_lower]


def filter_sendgrid(records: Iterable[Record]) -> List[Record]:
    return [
        record
        for record in records
        if "sendgrid" in record.name_lower or "sendgrid" in record.rdata_lower
    ]


def filter_tor(records: Iterable[Record]) -> List[Record]:
    return [record for record in records if "tor" in record.name_lower]


def format_section(title: str, records: List[Record]) -> str:
    header = f"=== {title} ==="
    if not records:
        return f"{header}\n(no matches)\n"

    sorted_records = sorted(records, key=lambda r: (r.name_lower, r.type_upper))
    name_width = max(len(r.name) for r in sorted_records)
    type_width = max(len(r.type) for r in sorted_records)
    ttl_width = max(len(r.ttl) for r in sorted_records)

    lines = [header, f"{'Name'.ljust(name_width)}  {'Type'.ljust(type_width)}  {'TTL'.ljust(ttl_width)}  RDATA"]
    for record in sorted_records:
        lines.append(
            f"{record.name.ljust(name_width)}  "
            f"{record.type.ljust(type_width)}  "
            f"{record.ttl.ljust(ttl_width)}  "
            f"{record.rdata}"
        )
    lines.append("")
    return "\n".join(lines)


def build_report(records: List[Record]) -> str:
    sections = [
        ("CAA Issue Records (non-allowed)", filter_caa_exceptions(records)),
        ("Email Records", filter_email(records)),
        ("FTP Records", filter_ftp(records)),
        ("NS Records", filter_ns(records)),
        ("Relay Records", filter_relay(records)),
        ("Sendgrid Records", filter_sendgrid(records)),
        ("Tor Records", filter_tor(records)),
    ]
    return "\n".join(format_section(title, subset) for title, subset in sections).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate DNS report from CSV export.")
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to filogix.com CSV (e.g., /Users/paulabailey/Downloads/filogix.com.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_records(args.csv_path.expanduser().resolve())
    report = build_report(records)
    print(report)


if __name__ == "__main__":
    main()


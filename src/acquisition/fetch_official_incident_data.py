#!/usr/bin/env python3
"""Fetch immutable official snapshots for the 2026 Kumamoto earthquake water study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "2026_kumamoto_earthquake"
USER_AGENT = "KE01d-research/1.0 (+official-source-archiving)"


STATIC_SOURCES = [
    (
        "yatsushiro_water_points_current",
        "municipal/yatsushiro_water_points_current.html",
        "https://www.city.yatsushiro.lg.jp/kiji00326773/index.html",
        "Current emergency water points, hours, and per-visit allowance.",
    ),
    (
        "yatsushiro_shelters_current_page",
        "municipal/yatsushiro_shelters_current.html",
        "https://www.city.yatsushiro.lg.jp/kiji00326798/index.html",
        "Current shelter status landing page.",
    ),
    (
        "yatsushiro_shelters_20260806_1800",
        "municipal/yatsushiro_shelters_20260806_1800.pdf",
        "https://www.city.yatsushiro.lg.jp/kiji00326798/3_26798_158085_up_j2hekzza.pdf",
        "Facility-level shelter occupancy and utility conditions.",
    ),
    (
        "uki_water_outage_current",
        "municipal/uki_water_outage_current.html",
        "https://www.city.uki.kumamoto.jp/kurashi/sumai/jogesuido/2606682",
        "Current outage, pressure-restriction, water-point, and restoration details.",
    ),
    (
        "hikawa_emergency_current",
        "municipal/hikawa_emergency_current.html",
        "https://www.town.hikawa.kumamoto.jp/kinkyu.html",
        "Current emergency water points, hours, and per-visit allowance.",
    ),
    (
        "kumamoto_prefecture_incident_hub",
        "prefecture/kumamoto_prefecture_incident_hub.html",
        "https://www.pref.kumamoto.jp/soshiki/1/274517.html",
        "Prefecture incident information hub.",
    ),
    (
        "kumamoto_prefecture_snapshot_20260807_1400",
        "prefecture/kumamoto_prefecture_snapshot_20260807_1400.pdf",
        "https://www.pref.kumamoto.jp/uploaded/attachment/316396.pdf",
        "Municipal shelter, evacuee, outage-household, and water-point counts.",
    ),
    (
        "mlit_incident_reports_index",
        "mlit_reports/index.html",
        "https://www.mlit.go.jp/saigai/saigai_260728.html",
        "MLIT incident report index used to discover timestamped situation reports.",
    ),
    (
        "mlit_passable_roads_index",
        "road_status/index.html",
        "https://www.mlit.go.jp/road/saigai/r8kumamoto/index.html",
        "MLIT passable-roads map and dated GIS download index.",
    ),
]


ROAD_ARCHIVES = [
    ("20260729_0800", "260729data.zip"),
    ("20260729_1200", "2607291200data.zip"),
    ("20260730_0800", "2607300800data.zip"),
    ("20260730_1200", "2607301200data.zip"),
    ("20260730_1600", "2607301600data.zip"),
    ("20260731_0800", "2607310800data.zip"),
    ("20260731_1600", "2607311600data.zip"),
    ("20260801_1800", "2608011800data.zip"),
    ("20260802_1800", "2608021800data.zip"),
    ("20260803_1200", "2608031200data.zip"),
    ("20260803_1600", "2608031600data.zip"),
    ("20260804_1300", "2608041300data.zip"),
    ("20260804_1600", "2608041600data.zip"),
    ("20260805_1300", "2608051300data.zip"),
    ("20260806_1300", "2608061300data.zip"),
    ("20260807_1600", "2608071600data.zip"),
    ("current", "map.zip"),
]


@dataclass
class ManifestRow:
    source_id: str
    url: str
    retrieved_at_utc: str
    status: str
    http_status: int | None
    sha256: str
    bytes: int | None
    relative_path: str
    notes: str


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = dict(attrs).get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fetch_one(
    session: requests.Session,
    output_root: Path,
    source_id: str,
    relative_path: str,
    url: str,
    notes: str,
) -> tuple[ManifestRow, bytes | None]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    target = output_root / relative_path
    try:
        response = session.get(url, timeout=60)
        response.raise_for_status()
        payload = response.content
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return (
            ManifestRow(
                source_id=source_id,
                url=url,
                retrieved_at_utc=retrieved_at,
                status="downloaded",
                http_status=response.status_code,
                sha256=sha256_bytes(payload),
                bytes=len(payload),
                relative_path=str(target.relative_to(PROJECT_ROOT)),
                notes=notes,
            ),
            payload,
        )
    except requests.RequestException as exc:
        status = exc.response.status_code if exc.response is not None else None
        return (
            ManifestRow(
                source_id=source_id,
                url=url,
                retrieved_at_utc=retrieved_at,
                status="failed",
                http_status=status,
                sha256="",
                bytes=None,
                relative_path=str(target.relative_to(PROJECT_ROOT)),
                notes=f"{notes} Error: {exc}",
            ),
            None,
        )


def discover_mlit_reports(index_payload: bytes, index_url: str) -> list[tuple[str, str, str, str]]:
    text = index_payload.decode("utf-8", errors="replace")
    parser = LinkCollector()
    parser.feed(text)
    reports: list[tuple[str, str, str, str]] = []
    seen: set[str] = set()
    for href, label in parser.links:
        url = urljoin(index_url, href)
        if url in seen or not urlparse(url).path.lower().endswith(".pdf"):
            continue
        normalized = re.sub(r"\s+", " ", label)
        if not ("被害状況等について" in normalized or "熊本県熊本地方を震源" in normalized):
            continue
        seen.add(url)
        report_number = re.search(r"第\s*(\d+)\s*報", normalized)
        if report_number:
            file_stem = f"report_{int(report_number.group(1)):02d}"
        else:
            file_stem = "report_01"
        reports.append(
            (
                f"mlit_{file_stem}",
                f"mlit_reports/{file_stem}.pdf",
                url,
                normalized,
            )
        )
    return sorted(reports, key=lambda item: item[0])


def write_manifest(output_root: Path, rows: list[ManifestRow]) -> Path:
    manifest_path = output_root / "source_manifest.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(ManifestRow.__annotations__)
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_root = args.output.resolve()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    rows: list[ManifestRow] = []
    downloaded_payloads: dict[str, bytes] = {}

    for source_id, relative_path, url, notes in STATIC_SOURCES:
        row, payload = fetch_one(session, output_root, source_id, relative_path, url, notes)
        rows.append(row)
        if payload is not None:
            downloaded_payloads[source_id] = payload

    index_payload = downloaded_payloads.get("mlit_incident_reports_index")
    if index_payload is not None:
        for source in discover_mlit_reports(
            index_payload,
            "https://www.mlit.go.jp/saigai/saigai_260728.html",
        ):
            row, _ = fetch_one(session, output_root, *source)
            rows.append(row)

    road_base = "https://www.mlit.go.jp/road/saigai/r8kumamoto/"
    for snapshot, filename in ROAD_ARCHIVES:
        row, _ = fetch_one(
            session,
            output_root,
            f"mlit_road_status_{snapshot}",
            f"road_status/{snapshot}_{filename}",
            urljoin(road_base, filename),
            "Dated road restriction and ETC2.0 average-speed GIS archive.",
        )
        rows.append(row)

    manifest_path = write_manifest(output_root, rows)
    downloaded = sum(row.status == "downloaded" for row in rows)
    failed = sum(row.status == "failed" for row in rows)
    print(f"output={output_root}")
    print(f"manifest={manifest_path}")
    print(f"downloaded={downloaded}")
    print(f"failed={failed}")
    for row in rows:
        if row.status == "failed":
            print(f"FAILED {row.source_id}: HTTP {row.http_status} {row.url}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

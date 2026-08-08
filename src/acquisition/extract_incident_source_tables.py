#!/usr/bin/env python3
"""Extract reviewable source tables from archived official incident snapshots."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import unicodedata
import zipfile
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "data" / "raw" / "2026_kumamoto_earthquake"
EXTRACTED = RAW_ROOT / "extracted"
JST_OFFSET = "+09:00"


class TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", unescape(data)).strip()
        if value:
            self.chunks.append(value)


def html_chunks(path: Path) -> list[str]:
    parser = TextCollector()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.chunks


def parse_time_range(value: str) -> tuple[str, str] | None:
    normalized = unicodedata.normalize("NFKC", value)
    match = re.search(r"(\d{1,2}):(\d{2})\s*[~〜～-]\s*(\d{1,2}):(\d{2})", normalized)
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}", f"{int(match.group(3)):02d}:{match.group(4)}"


def manifest_lookup() -> dict[str, dict[str, str]]:
    with (RAW_ROOT / "source_manifest.csv").open(encoding="utf-8", newline="") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle)}


def water_point_row(
    municipality: str,
    name: str,
    valid_from: str,
    valid_to: str,
    opening: str,
    closing: str,
    allocation_basis: str,
    allocation_limit: float,
    source_status_time: str,
    source: dict[str, str],
) -> dict[str, Any]:
    return {
        "municipality": municipality,
        "water_point_name": name,
        "valid_from_date": valid_from,
        "valid_to_date": valid_to,
        "opening_time": opening,
        "closing_time": closing,
        "allocation_basis": allocation_basis,
        "allocation_limit_liters": allocation_limit,
        "water_type": "unspecified emergency supply",
        "source_status_time": source_status_time,
        "source_url": source["url"],
        "source_file": source["relative_path"],
        "source_retrieved_at_utc": source["retrieved_at_utc"],
        "latitude": None,
        "longitude": None,
        "location_resolution_status": "pending facility-name match",
    }


def extract_yatsushiro_water_points(source: dict[str, str]) -> list[dict[str, Any]]:
    chunks = html_chunks(ROOT / source["relative_path"])
    start = next(i for i, value in enumerate(chunks) if "応急給水活動について" in value)
    end = next(i for i, value in enumerate(chunks[start:], start) if "給水場所等のマップ" in value)
    rows: list[dict[str, Any]] = []
    current_range: tuple[str, str] | None = None
    accepting_points = False
    for value in chunks[start:end]:
        time_range = parse_time_range(value)
        if time_range:
            current_range = time_range
            accepting_points = False
            continue
        if "場所（以下順不同）" in value:
            accepting_points = True
            continue
        if not accepting_points or not value.startswith("・") or current_range is None:
            continue
        name = value.lstrip("・").strip()
        rows.append(
            water_point_row(
                "八代市",
                name,
                "2026-08-08",
                "2026-08-08",
                current_range[0],
                current_range[1],
                "per visit (approximately)",
                10.0,
                f"2026-08-07T21:00:00{JST_OFFSET}",
                source,
            )
        )
    if len(rows) != 28:
        raise RuntimeError(f"Expected 28 Yatsushiro water points, extracted {len(rows)}")
    return rows


def extract_uki_water_points(source: dict[str, str]) -> list[dict[str, Any]]:
    chunks = html_chunks(ROOT / source["relative_path"])
    supply_start = next(i for i, value in enumerate(chunks) if value == "給水について")
    place_start = next(i for i, value in enumerate(chunks[supply_start:], supply_start) if value == "場所")
    end = next(i for i, value in enumerate(chunks[place_start + 1 :], place_start + 1) if value == "留意事項")
    excluded = {"場所", "留意事項", "日時", "日付", "時間"}
    names: list[str] = []
    for value in chunks[place_start + 1 : end]:
        candidate = value.lstrip("・•").strip()
        if not candidate or candidate in excluded or candidate.startswith("※"):
            continue
        if any(token in candidate for token in ["7月29日", "午前8時30分", "断水が解消"]):
            continue
        names.append(candidate)
    rows = [
        water_point_row(
            "宇城市",
            name,
            "2026-07-29",
            "until outage resolution",
            "08:30",
            "17:00",
            "per person per day (maximum)",
            4.0,
            f"2026-08-07T17:00:00{JST_OFFSET}",
            source,
        )
        for name in names
    ]
    if len(rows) != 6:
        raise RuntimeError(f"Expected 6 Uki water points, extracted {len(rows)}: {names}")
    return rows


def extract_hikawa_water_points(source: dict[str, str]) -> list[dict[str, Any]]:
    chunks = html_chunks(ROOT / source["relative_path"])
    start = next(i for i, value in enumerate(chunks) if value == "給水車による応急給水について")
    section = chunks[start : start + 25]
    time_range = next((parse_time_range(value) for value in section if parse_time_range(value)), None)
    location_line = next(value for value in section if value.startswith("場所:" ) or value.startswith("場所："))
    names = re.split(r"[、,]", re.sub(r"^場所[:：]\s*", "", location_line))
    if time_range is None:
        raise RuntimeError("Hikawa water-point operating time was not found")
    rows = [
        water_point_row(
            "氷川町",
            name.strip(),
            "2026-08-06",
            "until superseded",
            time_range[0],
            time_range[1],
            "per visit (maximum)",
            10.0,
            f"2026-08-06T19:00:00{JST_OFFSET}",
            source,
        )
        for name in names
        if name.strip()
    ]
    if len(rows) != 2:
        raise RuntimeError(f"Expected 2 Hikawa water points, extracted {len(rows)}: {names}")
    return rows


def pdf_text(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return unicodedata.normalize("NFKC", result.stdout)


def extract_yatsushiro_shelters(source: dict[str, str]) -> list[dict[str, Any]]:
    text = pdf_text(ROOT / source["relative_path"])
    pattern = re.compile(
        r"^\s*(\d+)\s+(.+?)\s+(\S+)\s+([\d,]+)\s+(\d+)\s+(\d+)\s+([○〇△×])\s+([○〇△×])\s+([○〇△×])\s+(\d+)\s+(\d+)\s*$",
        re.MULTILINE,
    )
    rows: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        rows.append(
            {
                "municipality": "八代市",
                "shelter_number": int(match.group(1)),
                "shelter_name": match.group(2).strip(),
                "district": match.group(3),
                "maximum_capacity": int(match.group(4).replace(",", "")),
                "evacuee_households": int(match.group(5)),
                "evacuee_people": int(match.group(6)),
                "water_status_symbol": match.group(7).replace("〇", "○"),
                "electricity_status_symbol": match.group(8).replace("〇", "○"),
                "air_conditioning_status_symbol": match.group(9).replace("〇", "○"),
                "toilet_count": int(match.group(10)),
                "portable_toilet_count": int(match.group(11)),
                "snapshot_time": f"2026-08-06T18:00:00{JST_OFFSET}",
                "source_url": source["url"],
                "source_file": source["relative_path"],
                "source_retrieved_at_utc": source["retrieved_at_utc"],
                "latitude": None,
                "longitude": None,
                "location_resolution_status": "pending facility-name match",
            }
        )
    if len(rows) != 41:
        raise RuntimeError(f"Expected 41 Yatsushiro shelters, extracted {len(rows)}")
    return rows


def parse_japanese_timestamp(value: str) -> str | None:
    normalized = unicodedata.normalize("NFKC", value)
    match = re.search(r"2026年\s*(\d+)月\s*(\d+)日\s*(\d+):(\d+)", normalized)
    if not match:
        return None
    return f"2026-{int(match.group(1)):02d}-{int(match.group(2)):02d}T{int(match.group(3)):02d}:{match.group(4)}:00{JST_OFFSET}"


def parse_water_status_timestamp(text: str, report_timestamp: str | None) -> str | None:
    match = re.search(r"■水道\((\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})\s*時点\)", text)
    if not match:
        return report_timestamp
    return f"2026-{int(match.group(1)):02d}-{int(match.group(2)):02d}T{int(match.group(3)):02d}:{match.group(4)}:00{JST_OFFSET}"


def parse_household_count(value: str) -> float | None:
    cleaned = re.sub(r"[^0-9.,]", "", value)
    if not cleaned:
        return None
    if re.fullmatch(r"\d{1,3}\.\d{3}", cleaned):
        cleaned = cleaned.replace(".", "")
    else:
        cleaned = cleaned.replace(",", "")
    return float(cleaned)


MUNICIPALITIES = [
    "熊本市",
    "八代市",
    "宇土市",
    "上天草市",
    "宇城市",
    "天草市",
    "合志市",
    "御船町",
    "益城町",
    "甲佐町",
    "氷川町",
    "芦北町",
    "人吉市",
    "柳川市",
    "太良町",
    "南島原市",
]


def parse_outage_rows(text: str) -> list[dict[str, Any]]:
    water_start = text.find("■水道")
    if water_start < 0:
        return []
    water_end = text.find("■下水道", water_start)
    section = text[water_start : water_end if water_end >= 0 else None]
    rows: list[dict[str, Any]] = []
    for municipality in MUNICIPALITIES:
        pattern = re.compile(
            rf"^\s*{re.escape(municipality)}\s+(約\s*[\d,.]+|[\d,.]+|不明)\s+(約\s*[\d,.]+|[\d,.]+(?:※)?|不明)\s+([^\s]+)(.*)$",
            re.MULTILINE,
        )
        match = pattern.search(section)
        if not match:
            continue
        rows.append(
            {
                "reporting_unit_type": "municipality",
                "reporting_unit": municipality,
                "maximum_outage_households": parse_household_count(match.group(1)),
                "current_outage_households": parse_household_count(match.group(2)),
                "outage_period_text": match.group(3).strip(),
                "damage_status_text": match.group(4).strip(" ・"),
                "outage_raw_line": re.sub(r"\s+", " ", match.group(0)).strip(),
            }
        )
    return rows


def parse_tanker_rows(text: str) -> dict[str, dict[str, Any]]:
    start = text.find("給水車の派遣状況")
    if start < 0:
        return {}
    end = text.find("■下水道", start)
    section = text[start : end if end >= 0 else None]
    result: dict[str, dict[str, Any]] = {}
    units = ["八代市", "宇城市", "宇土市", "上天草市", "御船町", "益城町", "甲佐町", "嘉島町", "山都町"]
    for unit in units:
        match = re.search(rf"^\s*{re.escape(unit)}\s+([0-9\s]+)$", section, re.MULTILINE)
        if not match:
            continue
        values = [int(value) for value in re.findall(r"\d+", match.group(1))]
        row: dict[str, Any] = {
            "tanker_total": values[0] if values else None,
            "tanker_mlit": None,
            "tanker_jwwa": None,
            "tanker_sdf": None,
            "tanker_parse_status": "total only" if values else "unparsed",
            "tanker_raw_line": re.sub(r"\s+", " ", match.group(0)).strip(),
        }
        if len(values) == 4:
            row.update(
                {
                    "tanker_mlit": values[1],
                    "tanker_jwwa": values[2],
                    "tanker_sdf": values[3],
                    "tanker_parse_status": "complete",
                }
            )
        result[unit] = row

    joint_match = re.search(r"八代(?:生活)?環境事務組合(.{0,260}?)(?:甲佐町|宇城市)", section, re.DOTALL)
    if joint_match:
        block = joint_match.group(0)
        number_lines = [
            [int(value) for value in re.findall(r"\d+", line)]
            for line in block.splitlines()
            if re.search(r"\d", line)
        ]
        main_values = next((values for values in number_lines if len(values) >= 3), [])
        sdf_values = [values[0] for values in number_lines if len(values) == 1]
        if main_values:
            result["八代環境事務組合"] = {
                "tanker_total": main_values[0],
                "tanker_mlit": main_values[1] if len(main_values) > 1 else None,
                "tanker_jwwa": main_values[2] if len(main_values) > 2 else None,
                "tanker_sdf": sdf_values[0] if sdf_values else None,
                "tanker_parse_status": "complete" if sdf_values else "partial",
                "tanker_raw_line": re.sub(r"\s+", " ", block).strip(),
            }
    return result


def extract_outage_tanker_snapshots(manifest: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for report_number in range(1, 34):
        source_id = f"mlit_report_{report_number:02d}"
        source = manifest[source_id]
        text = pdf_text(ROOT / source["relative_path"])
        report_timestamp = parse_japanese_timestamp(source["notes"])
        water_status_timestamp = parse_water_status_timestamp(text, report_timestamp)
        outage_rows = parse_outage_rows(text)
        tanker_rows = parse_tanker_rows(text)
        merged_units = {row["reporting_unit"] for row in outage_rows} | set(tanker_rows)
        outage_by_unit = {row["reporting_unit"]: row for row in outage_rows}
        for unit in sorted(merged_units):
            row: dict[str, Any] = {
                "report_number": report_number,
                "report_timestamp": report_timestamp,
                "water_status_timestamp": water_status_timestamp,
                "reporting_unit_type": "joint water operator" if unit == "八代環境事務組合" else "municipality",
                "reporting_unit": unit,
                "maximum_outage_households": None,
                "current_outage_households": None,
                "outage_period_text": None,
                "damage_status_text": None,
                "tanker_total": None,
                "tanker_mlit": None,
                "tanker_jwwa": None,
                "tanker_sdf": None,
                "tanker_parse_status": None,
                "outage_raw_line": None,
                "tanker_raw_line": None,
                "source_url": source["url"],
                "source_file": source["relative_path"],
                "source_retrieved_at_utc": source["retrieved_at_utc"],
            }
            row.update(outage_by_unit.get(unit, {}))
            row.update(tanker_rows.get(unit, {}))
            rows.append(row)
    return rows


def snapshot_iso_from_filename(path: Path) -> str:
    match = re.match(r"(\d{8})_(\d{4})_", path.name)
    if not match:
        raise ValueError(f"Cannot parse road snapshot timestamp from {path.name}")
    value = datetime.strptime("".join(match.groups()), "%Y%m%d%H%M")
    return value.strftime(f"%Y-%m-%dT%H:%M:00{JST_OFFSET}")


def extract_road_tables(manifest: dict[str, dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    restrictions: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    url_by_path = {row["relative_path"]: row for row in manifest.values()}
    archives = sorted(path for path in (RAW_ROOT / "road_status").glob("20*.zip"))
    for archive in archives:
        snapshot_time = snapshot_iso_from_filename(archive)
        relative_path = str(archive.relative_to(ROOT))
        source = url_by_path[relative_path]
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.namelist():
                if not member.lower().endswith(".geojson"):
                    continue
                data = json.load(bundle.open(member))
                features = data.get("features", [])
                property_fields = sorted({key for feature in features for key in (feature.get("properties") or {})})
                geometry_types = sorted(
                    {
                        value
                        for feature in features
                        if (value := (feature.get("geometry") or {}).get("type")) is not None
                    }
                )
                colors = sorted(
                    {
                        value
                        for feature in features
                        if (value := (feature.get("properties") or {}).get("_color")) is not None
                    }
                )
                inventory.append(
                    {
                        "snapshot_time": snapshot_time,
                        "layer_name": member,
                        "feature_count": len(features),
                        "property_fields_json": json.dumps(property_fields, ensure_ascii=False),
                        "geometry_types_json": json.dumps(geometry_types, ensure_ascii=False),
                        "style_colors_json": json.dumps(colors, ensure_ascii=False),
                        "source_url": source["url"],
                        "source_file": relative_path,
                        "source_retrieved_at_utc": source["retrieved_at_utc"],
                    }
                )
                if Path(member).name != "dourokisei.geojson":
                    continue
                for feature_index, feature in enumerate(features, start=1):
                    row = {
                        "snapshot_time": snapshot_time,
                        "feature_index": feature_index,
                        **(feature.get("properties") or {}),
                        "geometry_type": (feature.get("geometry") or {}).get("type"),
                        "geometry_json": json.dumps(feature.get("geometry"), ensure_ascii=False, separators=(",", ":")),
                        "source_url": source["url"],
                        "source_file": relative_path,
                        "source_retrieved_at_utc": source["retrieved_at_utc"],
                    }
                    restrictions.append(row)
    return restrictions, inventory


def write_table(name: str, rows: list[dict[str, Any]]) -> Path:
    path = EXTRACTED / name
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def main() -> int:
    manifest = manifest_lookup()
    water_points = [
        *extract_yatsushiro_water_points(manifest["yatsushiro_water_points_current"]),
        *extract_uki_water_points(manifest["uki_water_outage_current"]),
        *extract_hikawa_water_points(manifest["hikawa_emergency_current"]),
    ]
    shelters = extract_yatsushiro_shelters(manifest["yatsushiro_shelters_20260806_1800"])
    outage_tankers = extract_outage_tanker_snapshots(manifest)
    road_restrictions, road_inventory = extract_road_tables(manifest)

    outputs = {
        "emergency_water_points.csv": water_points,
        "shelters_current.csv": shelters,
        "outage_tanker_snapshots.csv": outage_tankers,
        "road_restrictions.csv": road_restrictions,
        "road_layer_inventory.csv": road_inventory,
    }
    for name, rows in outputs.items():
        path = write_table(name, rows)
        print(f"{path.relative_to(ROOT)} rows={len(rows)} columns={len(pd.DataFrame(rows).columns)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

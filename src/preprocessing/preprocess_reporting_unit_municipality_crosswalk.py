#!/usr/bin/env python3
"""Create an explicit reporting-unit-to-municipality crosswalk."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTAGES = ROOT / "data/processed/outage_tanker_snapshots_preprocessed.parquet"
ADMIN = ROOT / "data/processed/kumamoto_administrative_areas_preprocessed.parquet"
DESTINATION = ROOT / "data/processed/reporting_unit_municipality_crosswalk_preprocessed.parquet"

outages = pd.read_parquet(OUTAGES, columns=["Reporting Unit Type", "Reporting Unit"])
units = outages.drop_duplicates().sort_values(["Reporting Unit Type", "Reporting Unit"]).reset_index(drop=True)
admin = pd.read_parquet(ADMIN, columns=["Municipality Code", "Municipality Name"])
admin = admin.drop_duplicates("Municipality Name")
admin_lookup = dict(zip(admin["Municipality Name"], admin["Municipality Code"]))
admin_lookup["熊本市"] = "43100"

outside = {"南島原市": "長崎県", "太良町": "佐賀県", "柳川市": "福岡県"}
records = []
for unit_type, unit in units.itertuples(index=False, name=None):
    if unit_type == "joint water operator":
        records.append({
            "Reporting Unit Type": unit_type,
            "Reporting Unit": unit,
            "Reporting Prefecture": "熊本県",
            "Reporting Municipality Code": pd.NA,
            "Reporting Municipality Name": pd.NA,
            "Municipality Match Status": "joint_operator_unallocated",
            "In Kumamoto Study Area": True,
            "Joint Operator Area Status": "service_area_unresolved",
        })
    elif unit in outside:
        records.append({
            "Reporting Unit Type": unit_type,
            "Reporting Unit": unit,
            "Reporting Prefecture": outside[unit],
            "Reporting Municipality Code": pd.NA,
            "Reporting Municipality Name": unit,
            "Municipality Match Status": "outside_kumamoto_scope",
            "In Kumamoto Study Area": False,
            "Joint Operator Area Status": "not_applicable",
        })
    elif unit in admin_lookup:
        records.append({
            "Reporting Unit Type": unit_type,
            "Reporting Unit": unit,
            "Reporting Prefecture": "熊本県",
            "Reporting Municipality Code": admin_lookup[unit],
            "Reporting Municipality Name": unit,
            "Municipality Match Status": "exact_official_name",
            "In Kumamoto Study Area": True,
            "Joint Operator Area Status": "not_applicable",
        })
    else:
        records.append({
            "Reporting Unit Type": unit_type,
            "Reporting Unit": unit,
            "Reporting Prefecture": pd.NA,
            "Reporting Municipality Code": pd.NA,
            "Reporting Municipality Name": pd.NA,
            "Municipality Match Status": "unmatched",
            "In Kumamoto Study Area": pd.NA,
            "Joint Operator Area Status": "not_applicable",
        })

frame = pd.DataFrame(records)
frame["Reporting Municipality Code"] = frame["Reporting Municipality Code"].astype("string")
frame["In Kumamoto Study Area"] = frame["In Kumamoto Study Area"].astype("boolean")
DESTINATION.parent.mkdir(parents=True, exist_ok=True)
frame.to_parquet(DESTINATION, index=False, engine="pyarrow")
print(f"Saved {len(frame):,} rows x {len(frame.columns)} cols -> {DESTINATION.relative_to(ROOT)}")

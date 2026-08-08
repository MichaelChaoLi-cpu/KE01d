#!/usr/bin/env python3
"""Aggregate mesh scenarios and attach latest observed municipal tanker fields."""
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from geoparquet_utils import _geo_metadata, _write_table

ROOT = Path(__file__).resolve().parents[2]
MESH_SCENARIOS = ROOT / "data/processed/population_mesh_outage_demand_scenarios_preprocessed.parquet"
MUNICIPALITIES = ROOT / "data/processed/kumamoto_reporting_municipalities_preprocessed.parquet"
OUTAGES = ROOT / "data/processed/outage_tanker_snapshots_preprocessed.parquet"
CROSSWALK = ROOT / "data/processed/reporting_unit_municipality_crosswalk_preprocessed.parquet"
DESTINATION = ROOT / "data/processed/municipality_outage_demand_scenarios_preprocessed.parquet"

mesh = pd.read_parquet(MESH_SCENARIOS)
group_columns = ["Reporting Municipality Code", "Reporting Municipality Name", "Outage Population Scenario", "Demand Scenario", "Per Capita Water Demand (L/person/day)"]
aggregated = mesh.groupby(group_columns, observed=True, dropna=False).agg(
    **{
        "Municipality Total Population": ("Total Population", "sum"),
        "Municipality Total Households": ("Total Households", "sum"),
        "Outage Snapshot Time": ("Outage Snapshot Time", "max"),
        "Current Outage Households": ("Current Outage Households", "max"),
        "Outage Observation Status": ("Outage Observation Status", "first"),
        "Outage Household Ratio": ("Outage Household Ratio", "max"),
        "Estimated Outage Population": ("Estimated Outage Population", lambda values: values.sum(min_count=1)),
        "Estimated Water Demand (L/day)": ("Estimated Water Demand (L/day)", lambda values: values.sum(min_count=1)),
    }
).reset_index()

crosswalk = pd.read_parquet(CROSSWALK)
outages = pd.read_parquet(OUTAGES)
mapped = outages.merge(
    crosswalk[["Reporting Unit Type", "Reporting Unit", "Reporting Municipality Code", "Municipality Match Status"]],
    on=["Reporting Unit Type", "Reporting Unit"], how="left",
)
mapped = mapped[mapped["Municipality Match Status"].eq("exact_official_name")]
latest_official_snapshot = mapped["Water Status Timestamp"].max()
current_snapshot = mapped[mapped["Water Status Timestamp"].eq(latest_official_snapshot)]
latest = current_snapshot.sort_values(["Water Status Timestamp", "Report Number"]).groupby(
    "Reporting Municipality Code", observed=True
).tail(1)
latest = latest[["Reporting Municipality Code", "Report Number", "Water Status Timestamp", "Maximum Outage Households", "Tanker Total", "MLIT Tankers", "JWWA Tankers", "SDF Tankers"]]

municipalities = pd.read_parquet(MUNICIPALITIES)[["Reporting Municipality Code", "Geometry"]]
frame = aggregated.merge(latest, on="Reporting Municipality Code", how="left").merge(
    municipalities, on="Reporting Municipality Code", how="left"
)
frame["Water Status Timestamp"] = frame["Water Status Timestamp"].combine_first(frame["Outage Snapshot Time"])
columns = ["Reporting Municipality Code", "Reporting Municipality Name", "Geometry", "Report Number", "Water Status Timestamp", "Maximum Outage Households", "Current Outage Households", "Outage Observation Status", "Tanker Total", "MLIT Tankers", "JWWA Tankers", "SDF Tankers", "Municipality Total Population", "Municipality Total Households", "Outage Household Ratio", "Outage Population Scenario", "Estimated Outage Population", "Demand Scenario", "Per Capita Water Demand (L/person/day)", "Estimated Water Demand (L/day)"]
frame = frame[columns]
geo = _geo_metadata(pq.read_table(MUNICIPALITIES))
_write_table(pa.Table.from_pandas(frame, preserve_index=False), DESTINATION, geo)
print(f"Saved {len(frame):,} rows x {len(frame.columns)} cols -> {DESTINATION.relative_to(ROOT)}")

#!/usr/bin/env python3
"""Link meshes to reporting municipalities and construct confirmed demand scenarios."""
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from geoparquet_utils import _geo_metadata, _write_table
from round2_utils import build_mesh_municipality_links, weighted_quantile

ROOT = Path(__file__).resolve().parents[2]
MESH = ROOT / "data/processed/kumamoto_population_mesh_125m_preprocessed.parquet"
MUNICIPALITIES = ROOT / "data/processed/kumamoto_reporting_municipalities_preprocessed.parquet"
OUTAGES = ROOT / "data/processed/outage_tanker_snapshots_preprocessed.parquet"
CROSSWALK = ROOT / "data/processed/reporting_unit_municipality_crosswalk_preprocessed.parquet"
DESTINATION = ROOT / "data/processed/population_mesh_outage_demand_scenarios_preprocessed.parquet"

links = build_mesh_municipality_links(MESH, MUNICIPALITIES)
crosswalk = pd.read_parquet(CROSSWALK)
outages = pd.read_parquet(OUTAGES)
mapped = outages.merge(
    crosswalk[["Reporting Unit Type", "Reporting Unit", "Reporting Municipality Code", "In Kumamoto Study Area", "Municipality Match Status"]],
    on=["Reporting Unit Type", "Reporting Unit"], how="left",
)
mapped = mapped[
    mapped["In Kumamoto Study Area"].fillna(False)
    & mapped["Reporting Municipality Code"].notna()
    & mapped["Municipality Match Status"].eq("exact_official_name")
]
latest = mapped.sort_values(["Water Status Timestamp", "Report Number"]).groupby(
    "Reporting Municipality Code", observed=True
).tail(1)
latest = latest[["Reporting Municipality Code", "Water Status Timestamp", "Current Outage Households"]].rename(
    columns={"Water Status Timestamp": "Outage Snapshot Time"}
)
base = links.merge(latest, on="Reporting Municipality Code", how="left")
base["Municipality Total Households"] = base.groupby("Reporting Municipality Code", dropna=False)["Total Households"].transform("sum").astype("Int64")
base["Municipality Household Share"] = (
    base["Total Households"] / base["Municipality Total Households"]
).astype("Float64")

reported = base["Current Outage Households"].notna()
zero = reported & base["Current Outage Households"].eq(0)
raw_ratio = base["Current Outage Households"] / base["Municipality Total Households"]
capped = reported & raw_ratio.gt(1)
base["Outage Household Ratio"] = raw_ratio.clip(lower=0, upper=1).astype("Float64")
base["Outage Observation Status"] = pd.Series("not_reported", index=base.index, dtype="string")
base.loc[zero, "Outage Observation Status"] = "reported_zero"
base.loc[reported & ~zero, "Outage Observation Status"] = "reported_positive"
base.loc[capped, "Outage Observation Status"] = "reported_positive_ratio_capped"

base["_persons_per_household"] = base["Total Population"] / base["Total Households"]
p90 = base.groupby("Reporting Municipality Code", observed=True).apply(
    lambda group: weighted_quantile(group["_persons_per_household"], group["Total Households"], 0.90),
    include_groups=False,
).to_dict()
base["_p90_household_size"] = base["Reporting Municipality Code"].map(p90)
allocated_households = base["Current Outage Households"] * base["Municipality Household Share"]

population_scenarios = {
    "lower_one_person_per_household": np.minimum(base["Total Population"], allocated_households),
    "proportional_central": base["Total Population"] * base["Outage Household Ratio"],
    "upper_p90_household_size": np.minimum(base["Total Population"], allocated_households * base["_p90_household_size"]),
}
demand_scenarios = {"minimum": 3.0, "basic": 10.0, "extended": 20.0}
parts = []
for population_label, population in population_scenarios.items():
    for demand_label, per_capita in demand_scenarios.items():
        part = base.copy()
        part["Outage Population Scenario"] = population_label
        part["Estimated Outage Population"] = pd.to_numeric(population, errors="coerce").astype("Float64")
        part["Demand Scenario"] = demand_label
        part["Per Capita Water Demand (L/person/day)"] = per_capita
        part["Estimated Water Demand (L/day)"] = part["Estimated Outage Population"] * per_capita
        parts.append(part)
frame = pd.concat(parts, ignore_index=True)
columns = ["Mesh Code", "Reporting Municipality Code", "Reporting Municipality Name", "Spatial Join Status", "Geometry", "Total Population", "Total Households", "Municipality Total Households", "Municipality Household Share", "Outage Snapshot Time", "Current Outage Households", "Outage Observation Status", "Outage Household Ratio", "Outage Population Scenario", "Estimated Outage Population", "Demand Scenario", "Per Capita Water Demand (L/person/day)", "Estimated Water Demand (L/day)"]
frame = frame[columns]
geo = _geo_metadata(pq.read_table(MESH))
_write_table(pa.Table.from_pandas(frame, preserve_index=False), DESTINATION, geo)
print(f"Saved {len(frame):,} rows x {len(frame.columns)} cols -> {DESTINATION.relative_to(ROOT)}")
print(f"Spatial join status: {links['Spatial Join Status'].value_counts(dropna=False).to_dict()}")

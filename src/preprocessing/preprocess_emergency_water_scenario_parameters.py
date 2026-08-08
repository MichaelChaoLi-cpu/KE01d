#!/usr/bin/env python3
"""Create the confirmed long-format emergency-water scenario parameter table."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "data/processed/emergency_water_scenario_parameters_preprocessed.parquet"

JWWA = "https://www.jwwa.or.jp/info/pdf/jishin_kunren_03_01.pdf"
FDMA = "https://www.fdma.go.jp/bousaikeikaku/kanto/tokyo/items/tokyo_shinsai_shiryou.pdf"
MLIT = "https://www.mlit.go.jp/report/press/port06_hh_000336.html"

rows = []
def add(name, levels, unit, evidence, source, notes):
    for level, value in levels:
        rows.append({"Parameter Name": name, "Scenario Level": level, "Parameter Value": str(value), "Parameter Unit": unit, "Evidence Class": evidence, "Evidence Source": source, "Parameter Notes": notes})

add("Per Capita Water Demand", [("minimum", 3), ("basic", 10), ("extended", 20)], "L/person/day", "mixed_official_and_research_sensitivity", JWWA, "3 L is an official preparedness reference; 10 and 20 L are research sensitivity levels.")
add("Tanker Capacity", [("low", 2000), ("central", 3000), ("high", 4000)], "L", "official_reference_sensitivity", f"{FDMA}; {MLIT}", "Reference capacities only; not the observed Kumamoto fleet.")
add("Daily Trip Limit", [("low", 3), ("central", 5), ("high", 7)], "trips/day", "mixed_official_and_research_sensitivity", FDMA, "Seven trips appears in an official capacity example; lower levels are sensitivities.")
add("Loading Time", [("short", 15), ("central", 30), ("long", 60)], "min/trip", "researcher_defined_sensitivity", "research scenario", "Not observed for the 2026 incident.")
add("Unloading Time", [("short", 15), ("central", 30), ("long", 60)], "min/trip", "researcher_defined_sensitivity", "research scenario", "Not observed for the 2026 incident.")
add("Daily Work Limit", [("short", 8), ("central", 10), ("long", 12)], "hours/day", "researcher_defined_sensitivity", "research scenario", "Not an observed duty roster.")
add("General Access Distance", [("strict", 250), ("central", 500), ("wide", 1000)], "m", "researcher_defined_sensitivity", "research scenario", "Accessibility threshold, not observed collection behavior.")
add("Older Resident Access Distance", [("strict", 250), ("wide", 500)], "m", "researcher_defined_sensitivity", "research scenario", "Priority-population sensitivity threshold.")
add("Outage Duration", [("short", 1), ("central", 3), ("long", 7)], "days", "researcher_defined_sensitivity", "research scenario", "Scenario duration, not a restoration forecast.")
add("Fleet Size", [("low", 5), ("central", 10), ("high", 20)], "vehicles", "researcher_defined_sensitivity", "research scenario", "Resource curve input, not observed available fleet.")
add("Road State", [("baseline", "baseline"), ("matched restrictions", "matched_restrictions_closed"), ("severe", "severe_disruption")], "category", "researcher_defined_sensitivity", "research scenario", "Applied only after restriction-to-edge matching.")
add("Water Point State", [("all resolved", "all_resolved_points"), ("reported schedule", "reported_schedule"), ("single failure", "single_point_failure")], "category", "researcher_defined_sensitivity", "research scenario", "Does not assert actual point capacity.")

frame = pd.DataFrame(rows)[["Parameter Name", "Scenario Level", "Parameter Value", "Parameter Unit", "Evidence Class", "Evidence Source", "Parameter Notes"]]
DESTINATION.parent.mkdir(parents=True, exist_ok=True)
frame.to_parquet(DESTINATION, index=False, engine="pyarrow")
print(f"Saved {len(frame):,} rows x {len(frame.columns)} cols -> {DESTINATION.relative_to(ROOT)}")

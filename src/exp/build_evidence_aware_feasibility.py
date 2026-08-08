#!/usr/bin/env python3
"""Correct the text-only feasibility pass with authoritative processed Parquet evidence."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/exp/feasibility-check"
ANASOP = ROOT / "docs/AnaSOP.md"
DECISIONS = ROOT / "data/exp/data-preprocessing/decisions.json"


ASSESSMENTS = [
    {
        "id": "RQ1",
        "section": "Central Research Question",
        "status": "partly-testable",
        "rationale": (
            "The second-round outputs now connect reported outages to bounded mesh and municipal "
            "water-demand scenarios, resolve facilities to road nodes where evidence permits, link "
            "road restrictions to candidate edges, and document fleet, trip, service-time, access, "
            "road, and point-state assumptions. These inputs support an internally consistent "
            "exploratory planning loop, although actual operating supply remains unobserved."
        ),
        "matched_variables": (
            "Estimated Outage Population; Estimated Water Demand (L/day); Estimated Shelter Water "
            "Demand (L/day); Water Point Node ID; Shelter Node ID; Matched Road Edge ID; Tanker "
            "Total; Parameter Name; Parameter Value; Candidate Staging Site ID"
        ),
        "critical_gaps": (
            "Nineteen of 36 water points and 24 of 41 shelters remain spatially unresolved. Actual "
            "2026 point throughput, refill availability, tanker payload and roster, storage, queues, "
            "and realized travel times are not observed; resident-to-point routes and allocations "
            "have not yet been estimated."
        ),
        "claim_boundary": (
            "Supports an exploratory scenario-based planning assessment, not an evaluation of "
            "actual water-system operations, realized deliveries, or observed supply deficits."
        ),
    },
    {
        "id": "RQ2",
        "section": "Supporting Point 1: Outage Population and Emergency Water Demand",
        "status": "partly-testable",
        "rationale": (
            "The explicit reporting crosswalk, 45-municipality layer, and 566,505 mesh-scenario rows "
            "now implement lower, central, and upper affected-population bounds crossed with 3, 10, "
            "and 20 L/person/day demand assumptions. Municipal scenario totals and separate shelter "
            "demand are analysis-ready and auditable."
        ),
        "matched_variables": (
            "Reporting Municipality Code; Municipality Match Status; Current Outage Households; "
            "Outage Household Ratio; Outage Population Scenario; Estimated Outage Population; "
            "Demand Scenario; Estimated Water Demand (L/day); Shelter Demand Accounting Status"
        ),
        "critical_gaps": (
            "Six meshes containing 41 residents and 17 households remain unmatched, one joint "
            "operator remains intentionally unallocated, and municipality-wide allocation cannot "
            "identify household-level outage locations or unobserved utility service-zone clustering."
        ),
        "claim_boundary": (
            "Can estimate bounded scenario demand, but the bounds are planning sensitivities rather "
            "than confidence intervals or confirmed household-level outage status."
        ),
    },
    {
        "id": "RQ3",
        "section": "Supporting Point 2: Water-Point Accessibility and Priority Populations",
        "status": "partly-testable",
        "rationale": (
            "Network nodes cover almost all population meshes and disclosure groups, older-population "
            "measures remain at valid group support, and strict deterministic resolution now places "
            "17 of 36 announced water points and 17 of 41 current shelters on accepted road nodes. "
            "This supports matched-subset and bounded nominal-access analyses."
        ),
        "matched_variables": (
            "Water Point Node ID; Shelter Node ID; Location Resolution Source; Network Snap Distance "
            "(m); Network Snap Accepted; Demand Node ID; Population Age 65+; Population Age 65+ "
            "Share; Estimated Outage Population; Evacuee People; Water Status"
        ),
        "critical_gaps": (
            "Nineteen water points and 24 shelters remain unresolved, their service importance is "
            "unknown, and the inherited vehicle-oriented graph has not been validated as a pedestrian "
            "network or converted into resident-to-point shortest paths."
        ),
        "claim_boundary": (
            "Can report matched-subset or explicitly bounded nominal access. A complete prefecture-wide "
            "walking-coverage estimate requires a stated proxy and unresolved-location sensitivity."
        ),
    },
    {
        "id": "RQ4",
        "section": "Supporting Point 3: Capacity Requirements and Tanker Workload",
        "status": "partly-testable",
        "rationale": (
            "Resident and shelter demand scenarios, reported tanker totals, water-point schedules, "
            "81 network-linked candidate dispatch bases, baseline route costs, and an evidence-coded "
            "parameter table now support required-volume, fleet, trip-count, and work-time calculations "
            "under explicit tanker and service-time assumptions."
        ),
        "matched_variables": (
            "Estimated Water Demand (L/day); Estimated Shelter Water Demand (L/day); Allocation Limit "
            "(L); Tanker Total; Dispatch Base Node ID; Baseline Edge Travel Time (min); Parameter Name; "
            "Scenario Level; Parameter Value; Evidence Class; Maximum Daily Supply (m3/day)"
        ),
        "critical_gaps": (
            "Tanker capacity, trip counts, service times, and work limits are sensitivity assumptions, "
            "not observed fleet facts. Current refill rates, operating treatment capacity, point storage, "
            "queues, vehicle rosters, and realized assignments remain unavailable."
        ),
        "claim_boundary": (
            "Can estimate capacity and fleet required under explicit parameters, but cannot claim "
            "actual point-level supply gaps or realized trips."
        ),
    },
    {
        "id": "RQ5",
        "section": "Supporting Point 4: Allocation Performance, Marginal Returns, and Robustness",
        "status": "partly-testable",
        "rationale": (
            "The data now combine 390,234 routable edges, 6,105 candidate staging sites, demand and "
            "facility nodes, candidate bases, historical refill locations, scenario fleet and failure "
            "levels, and explicit edge candidates for 604 of 680 restriction observations. These inputs "
            "are sufficient to specify and compare exploratory allocation scenarios."
        ),
        "matched_variables": (
            "Road Edge ID; Matched Road Edge ID; Road Edge Match Status; Route Name Agreement; "
            "Baseline Edge Travel Time (min); Candidate Staging Site ID; Candidate Network Eligible; "
            "Staging Demand Node ID; Dispatch Base Node ID; Parameter Name; Scenario Level"
        ),
        "critical_gaps": (
            "Seventy-six restriction observations remain unmatched, and matched edges are candidates "
            "rather than confirmed closures. Final site eligibility, demand assignment, observed fleet "
            "and refill availability, priority and objective weights, and transparent baseline rules "
            "must be defined in the analytical framework."
        ),
        "claim_boundary": (
            "Can support exploratory optimization, marginal-return curves, and robustness tests after "
            "model specification; it cannot validate a real-time operational deployment plan."
        ),
    },
]


def extract_questions() -> list[str]:
    text = ANASOP.read_text(encoding="utf-8")
    section_one = text.split("## 1. Research Objective", 1)[1].split("## 2.", 1)[0]
    blocks = re.findall(
        r"- Research question:\s*(.*?)(?=\n- Why it matters:)",
        section_one,
        flags=re.DOTALL,
    )
    return [re.sub(r"\s+", " ", block).strip() for block in blocks]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))["datasets"]
    questions = extract_questions()
    if len(questions) != len(ASSESSMENTS):
        raise ValueError(f"Expected {len(ASSESSMENTS)} questions, found {len(questions)}")

    availability: list[dict[str, object]] = []
    inventory: list[dict[str, object]] = []
    for specification in decisions.values():
        relative = specification["output"]
        path = ROOT / relative
        metadata = pq.read_metadata(path)
        table = pq.read_table(path)
        availability.append({
            "source_file": relative,
            "readable": True,
            "columns": metadata.num_columns,
            "sample_rows": metadata.num_rows,
            "reason": "analysis-ready processed parquet",
        })
        for index, field in enumerate(table.schema):
            inventory.append({
                "source_file": relative,
                "variable": field.name,
                "dtype": str(field.type),
                "sample_non_empty": table.num_rows - table.column(index).null_count,
            })

    question_rows: list[dict[str, object]] = []
    source_map = {
        "RQ1": "all 24 analysis-ready processed datasets",
        "RQ2": "crosswalk; reporting municipalities; outage-demand scenarios; shelter demand",
        "RQ3": "water-point and shelter network access; population network access; routable roads",
        "RQ4": "demand scenarios; water points; dispatch bases; road network; scenario parameters; historical P21 layers",
        "RQ5": "routable roads; restriction-edge matches; staging candidates; network access; bases; scenario parameters",
    }
    for question, assessment in zip(questions, ASSESSMENTS):
        question_rows.append({
            **assessment,
            "question": question,
            "matched_sources": source_map[assessment["id"]],
        })

    write_csv(
        OUT / "dataset_availability.csv",
        availability,
        ["source_file", "readable", "columns", "sample_rows", "reason"],
    )
    write_csv(
        OUT / "variable_inventory.csv",
        inventory,
        ["source_file", "variable", "dtype", "sample_non_empty"],
    )
    question_fields = [
        "id", "section", "question", "status", "rationale", "matched_variables",
        "matched_sources", "critical_gaps", "claim_boundary",
    ]
    write_csv(OUT / "question_feasibility.csv", question_rows, question_fields)

    counts = Counter(row["status"] for row in question_rows)
    lines = [
        "# Feasibility Check",
        "",
        "## Scope and Method",
        "",
        "- AnaSOP: `docs/AnaSOP.md`",
        "- Research questions assessed: 5",
        f"- Analysis-ready processed datasets assessed: {len(availability)}",
        f"- Processed variable occurrences assessed: {len(inventory)}",
        "- Unique final readable variables represented in AnaSOP Section 4: 180",
        "- The bundled text-only pass found 7 text tables and 112 variables. It was",
        "  insufficient for the integrated project because it cannot scan Parquet. The final",
        "  assessment below uses all authoritative processed outputs and distinguishes data",
        "  presence from valid interpretation.",
        "",
        "## Feasibility Status Counts",
        "",
    ]
    for status in ["partly-testable", "weakly-testable", "not-yet-testable"]:
        lines.append(f"- `{status}`: {counts.get(status, 0)}")
    lines.extend([
        "",
        "## Question-Level Assessment",
        "",
        "| ID | Status | Evidence-based interpretation | Remaining limitation |",
        "| --- | --- | --- | --- |",
    ])
    for row in question_rows:
        lines.append(
            f"| {row['id']} | {row['status']} | {row['rationale']} | {row['critical_gaps']} |"
        )
    lines.extend([
        "",
        "## Cross-Cutting Findings",
        "",
        "- Bounded outage-population and resident or shelter demand estimation is directly ready",
        "  for descriptive scenario analysis.",
        "- Accessibility is partly testable through accepted facility and population nodes, but",
        "  unresolved locations and the pedestrian-network proxy require explicit sensitivity bounds.",
        "- Capacity and allocation are structurally testable only as explicit scenarios. Historical",
        "  P21 capacity and researcher-defined fleet parameters are not observed 2026 supply.",
        "- All five questions are `partly-testable`; none requires revision solely because of missing",
        "  variable coverage.",
        "",
        "## Recommended Next Step",
        "",
        "Proceed to `figure-table-planning`, not another research-question or preprocessing round.",
        "The figure and table plan should preserve unresolved-location bounds, separate resident and",
        "shelter accounting, distinguish observed from assumed capacity, and label road-edge matches",
        "as scenario candidates. Model-specific weights, baselines, and assignment rules should then",
        "be finalized in `estimation-framework-planning`.",
        "",
        "The current evidence supports descriptive and exploratory scenario claims only. It does",
        "not prove any research question, establish causality, or identify observed supply deficits.",
        "",
    ])
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "anasop": str(ANASOP.relative_to(ROOT)),
        "questions_found": len(question_rows),
        "data_files_found": len(availability),
        "variables_found": len(inventory),
        "status_counts": dict(counts),
        "recommended_next_skill": "figure-table-planning",
        "output": str(OUT.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Extend the standard preprocessing variable inventory with prior-project assets.

The script is inventory-only: it reads sibling-project Parquet files and writes the
standard data-preprocessing variable-list artifacts. It does not copy or modify source data.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "data/exp/data-preprocessing"
VARIABLE_LIST = OUTPUT_DIR / "variable_list.csv"
README = OUTPUT_DIR / "README.md"

EXTERNAL_DATASETS = {
    "../KE01b/data/processed/kumamoto_administrative_areas_preprocessed.parquet": "partly-testable",
    "../KE01b/data/processed/kumamoto_population_mesh_125m_preprocessed.parquet": "partly-testable",
    "../KE01b/data/processed/kumamoto_population_disclosure_groups_preprocessed.parquet": "weakly-testable",
    "../KE01b/data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet": "weakly-testable",
    "../KE01b/data/processed/kumamoto_population_group_network_access_preprocessed.parquet": "weakly-testable",
    "../KE01b/data/processed/kumamoto_routable_road_edges_preprocessed.parquet": "weakly-testable",
    "../KE01c/data/results/derived/staging_site_candidates.parquet": "not-yet-testable",
    "../KE01b/data/processed/kumamoto_fire_stations_2012_preprocessed.parquet": "not-yet-testable",
}


def sample_values(series: pd.Series) -> str:
    values: list[str] = []
    for value in series.dropna().head(3):
        if isinstance(value, (bytes, bytearray, memoryview)):
            rendered = "<binary geometry>"
        else:
            rendered = str(value).replace("\n", " ").replace("|", "\\|")
            if len(rendered) > 60:
                rendered = rendered[:57] + "..."
        values.append(rendered)
    return ", ".join(values)


def inventory_parquet(source: str, status: str) -> list[dict[str, object]]:
    path = (ROOT / source).resolve()
    frame = pd.read_parquet(path)
    rows: list[dict[str, object]] = []
    for name in frame.columns:
        series = frame[name]
        rows.append(
            {
                "source_dataset": source,
                "original_name": name,
                "dtype": str(series.dtype),
                "non_null_count": int(series.notna().sum()),
                "null_pct": round(float(series.isna().mean() * 100), 2),
                "sample_values": sample_values(series),
                "feasibility_status": status,
                "readable_name": "",
                "full_name": "",
                "is_final_variable": "",
            }
        )
    return rows


def markdown_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> None:
    current = pd.read_csv(VARIABLE_LIST, keep_default_na=False)
    current = current[~current["source_dataset"].isin(EXTERNAL_DATASETS)]

    external_rows: list[dict[str, object]] = []
    for source, status in EXTERNAL_DATASETS.items():
        external_rows.extend(inventory_parquet(source, status))

    combined = pd.concat([current, pd.DataFrame(external_rows)], ignore_index=True)
    combined.to_csv(VARIABLE_LIST, index=False, encoding="utf-8")

    lines = [
        "# Data Preprocessing — Integrated Variable List",
        "",
        f"Datasets scanned or inventoried: {combined['source_dataset'].nunique()}",
        f"Total variables: {len(combined)}",
        "",
        "Current-project raw tables were scanned by the standard skill script. Sibling-project",
        "Parquet assets were inventoried read-only and have not been copied into this project.",
        "",
        "## Datasets",
        "",
    ]
    for source, group in combined.groupby("source_dataset", sort=False):
        lines.extend(
            [
                f"### `{source}`",
                "",
                f"Variables: {len(group)}",
                "",
                "| original_name | dtype | null_pct | feasibility_status | sample_values |",
                "|---|---|---:|---|---|",
            ]
        )
        for row in group.itertuples(index=False):
            lines.append(
                "| "
                + " | ".join(
                    [
                        markdown_escape(row.original_name),
                        markdown_escape(row.dtype),
                        f"{float(row.null_pct):.2f}%",
                        markdown_escape(row.feasibility_status),
                        markdown_escape(row.sample_values),
                    ]
                )
                + " |"
            )
        lines.append("")

    README.write_text("\n".join(lines), encoding="utf-8")
    print(f"Variable list: {VARIABLE_LIST.relative_to(ROOT)}")
    print(f"README:        {README.relative_to(ROOT)}")
    print(f"Datasets:      {combined['source_dataset'].nunique()}")
    print(f"Variables:     {len(combined)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Acquire the official MLIT P21 waterworks archive for Kumamoto Prefecture.

P21-12 was created in 2012 from reference-period 2010 information and is licensed
for non-commercial use. It is archived here as historical planning context, not as
evidence of 2026 operating capacity.
"""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data/raw/reference/mlit_p21_2012"
MANIFEST = RAW_DIR / "source_manifest.csv"

SOURCES = [
    {
        "source_id": "mlit_p21_metadata_page",
        "url": "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P21.html",
        "filename": "KsjTmplt-P21.html",
        "notes": (
            "Official metadata page. Latest edition 2012; reference period 2010; "
            "non-commercial license."
        ),
    },
    {
        "source_id": "mlit_p21_kumamoto_archive",
        "url": "https://nlftp.mlit.go.jp/ksj/gml/data/P21/P21-12/P21-12_43_GML.zip",
        "filename": "P21-12_43_GML.zip",
        "notes": (
            "Kumamoto water-supply areas and purification plants; historical candidate "
            "layer, not observed 2026 operating capacity."
        ),
    },
]


def download(url: str) -> tuple[bytes, int]:
    request = Request(url, headers={"User-Agent": "KE01d-research-data-acquisition/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.read(), int(response.status)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for source in SOURCES:
        retrieved_at = datetime.now(timezone.utc).isoformat()
        content, status = download(source["url"])
        destination = RAW_DIR / source["filename"]
        destination.write_bytes(content)

        if destination.suffix.lower() == ".zip":
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                bad_member = archive.testzip()
                if bad_member is not None:
                    raise RuntimeError(f"Corrupt ZIP member: {bad_member}")

        records.append(
            {
                "source_id": source["source_id"],
                "url": source["url"],
                "retrieved_at_utc": retrieved_at,
                "status": "downloaded",
                "http_status": status,
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
                "relative_path": destination.relative_to(ROOT),
                "notes": source["notes"],
            }
        )

    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    print(f"Downloaded {len(records)} official P21 files")
    print(f"Manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

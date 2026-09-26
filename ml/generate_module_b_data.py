"""Ingest real, pre-labeled URLs; no synthetic URLs or rule-generated labels.

Default source: Kaggle Web page Phishing Detection Dataset, version 2,
Hannousse & Yahiouche (May 2020 collection), CC BY 4.0. See data/README.md.
The similarly named UCI 327 dataset has numeric features, not raw URLs.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import zipfile

import pandas as pd

DOWNLOAD_URL = (
    "https://www.kaggle.com/api/v1/datasets/download/"
    "shashwatwork/web-page-phishing-detection-dataset?datasetVersionNumber=2"
)
SOURCE_PAGE = "https://www.kaggle.com/datasets/shashwatwork/web-page-phishing-detection-dataset"
ROOT = Path(__file__).resolve().parents[1]


def validate_urls(frame):
    """Validate canonical labels; deduplicate the lowercase text seen by TF-IDF."""
    if not {"url", "label"}.issubset(frame.columns):
        raise ValueError("Expected raw 'url' and 'label' columns, not numeric URL features.")
    frame = frame[["url", "label"]].copy()
    if frame.isna().any().any():
        raise ValueError("Missing URLs or labels are not allowed.")
    frame["url"] = frame["url"].astype(str).str.strip()
    frame["label"] = frame["label"].astype(str).str.strip().str.lower()
    if not frame["label"].isin(["phishing", "legitimate"]).all():
        raise ValueError("Labels must be phishing/legitimate; unknown labels cannot become legitimate.")
    for url in frame["url"]:
        try:
            parsed = urlsplit(url)
            valid = parsed.scheme in ("http", "https") and bool(parsed.hostname)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Every row must contain a nonempty HTTP(S) URL.")
    frame["_key"] = frame["url"].str.lower()
    if (frame.groupby("_key")["label"].nunique() > 1).any():
        raise ValueError("Conflicting labels for the same URL text.")
    frame = frame.drop_duplicates("_key").drop(columns="_key").reset_index(drop=True)
    if frame["label"].nunique() != 2:
        raise ValueError("Both phishing and legitimate examples are required.")
    return frame


def generate_module_b_data(source=None, output=ROOT / "data/raw/module_b_urls.csv"):
    """Read an upstream CSV/ZIP, or download the pinned public Kaggle ZIP."""
    if source is None:
        request = Request(DOWNLOAD_URL, headers={"User-Agent": "TrueIntent-ModuleB/1.0"})
        with urlopen(request, timeout=60) as response:
            payload = response.read()
    else:
        payload = Path(source).read_bytes()
    if zipfile.is_zipfile(io.BytesIO(payload)):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = [n for n in archive.namelist() if n.endswith(".csv")]
            if len(names) != 1:
                raise ValueError("Expected exactly one CSV in the source archive.")
            frame = pd.read_csv(archive.open(names[0]))
    else:
        frame = pd.read_csv(io.BytesIO(payload))
    if "label" not in frame.columns and "status" in frame.columns:
        frame = frame.rename(columns={"status": "label"})
    clean = validate_urls(frame)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        # Preserve pre-existing data of unknown provenance; never mix it in.
        digest = hashlib.sha256(output.read_bytes()).hexdigest()[:12]
        backup = output.with_name(output.name + f".before-{digest}.bak")
        if not backup.exists():
            shutil.copy2(output, backup)
    csv_bytes = clean.to_csv(index=False, lineterminator="\n").encode("utf-8")
    output.write_bytes(csv_bytes)
    metadata = {
        "source": SOURCE_PAGE if source is None else str(Path(source)),
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "input_rows": len(frame), "rows": len(clean),
        "duplicates_removed": len(frame) - len(clean),
        "class_counts": clean["label"].value_counts().to_dict(),
        "label_mapping": {"phishing": 1, "legitimate": 0},
        "transformations": "Select url/status (or label); trim; deduplicate lowercase URL text.",
        "synthetic_generation": False,
        "provenance_note": "Local inputs require their own provenance; see data/README.md for the verified Kaggle source.",
        "phishtank_supplement": "Not downloaded: current training-use terms unclear.",
    }
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return clean


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Downloaded upstream CSV or ZIP; omit to download Kaggle v2")
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/module_b_urls.csv")
    args = parser.parse_args()
    generate_module_b_data(args.source, args.output)

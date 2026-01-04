#!/usr/bin/env python3
"""Build a PII-safe demo CSV with pseudo embeddings from the demo JSON."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

EMBEDDING_COLUMN_CANDIDATES = ("embedding", "embeddings", "vector", "embedding_vector")
DEFAULT_DIM = 1024
DEFAULT_SEED = 42

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data_samples" / "demo_jobs_50.json"
DEFAULT_OUTPUT = ROOT / "data_samples" / "demo_jobs_50_with_embeddings.csv"
DEFAULT_DEMO_NAME = "demo_jobs_50_with_embeddings.csv"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build demo CSV (with pseudo-embeddings) from demo JSON")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input JSON path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output CSV path")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic seed")
    parser.add_argument("--limit", type=int, default=50, help="Max rows to emit")
    return parser.parse_args()


def _resolve_env_path(raw_value: Optional[str]) -> Optional[Path]:
    if not raw_value:
        return None
    value = raw_value.strip()
    if not value:
        return None
    path = Path(value).expanduser()
    if path.is_dir():
        return path / DEFAULT_DEMO_NAME
    return path


def _find_reference_csv() -> Optional[Path]:
    candidates: list[Path] = []

    for env_name in ("RAG_DATA_PATH", "SEED_PATH", "DATA_DIR"):
        env_path = _resolve_env_path(os.getenv(env_name))
        if env_path:
            candidates.append(env_path)

    candidates.extend(
        [
            ROOT / "data" / "new_work_with_embeddings.csv",
            ROOT / "data" / "job_seed_seniorforum_100_with_embeddings.csv",
            ROOT / "data_samples" / "demo_jobs_50_with_embeddings.csv",
        ]
    )

    for path in candidates:
        if path and path.exists() and path.suffix.lower() == ".csv":
            return path
    return None


def _detect_embedding_column(columns: Sequence[str]) -> str:
    for name in EMBEDDING_COLUMN_CANDIDATES:
        if name in columns:
            return name
    for col in columns:
        if "embedding" in col.lower():
            return col
    return "embedding"


def _parse_embedding_value(raw: str) -> Tuple[Optional[list[float]], str]:
    text = (raw or "").strip()
    if not text:
        return None, "bracketed"

    if text.startswith("[") and text.endswith("]"):
        try:
            data = json.loads(text)
        except Exception:
            try:
                data = eval(text)
            except Exception:
                return None, "bracketed"
        return [float(v) for v in data], "bracketed"

    if "," in text:
        parts = [p for p in re.split(r"[\s,]+", text) if p]
        try:
            return [float(v) for v in parts], "comma"
        except Exception:
            return None, "comma"

    parts = [p for p in re.split(r"\s+", text) if p]
    try:
        return [float(v) for v in parts], "space"
    except Exception:
        return None, "space"


def _infer_embedding_spec(reference_csv: Optional[Path]) -> Tuple[Sequence[str], str, int, str]:
    if not reference_csv:
        columns = [
            "job_id",
            "title",
            "participants",
            "hourly_wage",
            "place",
            "address",
            "work_days",
            "start_time",
            "end_time",
            "client",
            "description",
            "embedding",
        ]
        return columns, "embedding", DEFAULT_DIM, "bracketed"

    with reference_csv.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.reader(fp)
        header = next(reader, None)

    if not header:
        return [
            "job_id",
            "title",
            "participants",
            "hourly_wage",
            "place",
            "address",
            "work_days",
            "start_time",
            "end_time",
            "client",
            "description",
            "embedding",
        ], "embedding", DEFAULT_DIM, "bracketed"

    embedding_col = _detect_embedding_column(header)
    columns = list(header)
    if embedding_col not in columns:
        columns.append(embedding_col)
    dimension = DEFAULT_DIM
    fmt = "bracketed"

    with reference_csv.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            raw = row.get(embedding_col) if embedding_col else None
            vec, fmt_guess = _parse_embedding_value(raw or "")
            if vec:
                dimension = len(vec)
                fmt = fmt_guess
                break

    return columns, embedding_col, dimension, fmt


def _pseudo_embedding(text: str, dim: int, seed: int) -> list[float]:
    digest = hashlib.sha256(f"{seed}:{text}".encode("utf-8")).digest()
    seed_int = int.from_bytes(digest[:8], "big", signed=False)
    rng = random.Random(seed_int)
    return [rng.uniform(-1.0, 1.0) for _ in range(dim)]


def _format_embedding(values: Iterable[float], fmt: str) -> str:
    formatted = [f"{v:.6f}" for v in values]
    if fmt == "space":
        return " ".join(formatted)
    if fmt == "comma":
        return ",".join(formatted)
    return "[" + ", ".join(formatted) + "]"


def _coerce_int(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def main() -> None:
    args = _parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input JSON not found: {input_path}")

    rows = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("Input JSON must be a list")
    if args.limit is not None:
        rows = rows[: args.limit]

    reference_csv = _find_reference_csv()
    columns, embedding_col, dimension, fmt = _infer_embedding_spec(reference_csv)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(columns))
        writer.writeheader()

        for idx, record in enumerate(rows, start=1):
            title = str(record.get("title") or "").strip()
            description = str(record.get("description") or "").strip()
            text_for_embedding = " ".join([title, description]).strip()
            embedding = _format_embedding(
                _pseudo_embedding(text_for_embedding or f"demo-{idx}", dimension, args.seed),
                fmt,
            )

            row = {col: "" for col in columns}
            if "job_id" in row:
                row["job_id"] = idx
            if "title" in row:
                row["title"] = title
            if "participants" in row:
                row["participants"] = _coerce_int(record.get("participants"), 1)
            if "hourly_wage" in row:
                row["hourly_wage"] = _coerce_int(record.get("hourly_wage"), 0)
            if "place" in row:
                row["place"] = str(record.get("place") or "").strip()
            if "address" in row:
                row["address"] = str(record.get("location_label") or "").strip()
            if "work_days" in row:
                row["work_days"] = str(record.get("work_days") or "").strip()
            if "start_time" in row:
                row["start_time"] = str(record.get("start_time") or "").strip()
            if "end_time" in row:
                row["end_time"] = str(record.get("end_time") or "").strip()
            if "client" in row:
                row["client"] = str(record.get("client") or "").strip()
            if "description" in row:
                row["description"] = description
            if "lat" in row:
                row["lat"] = record.get("lat") or ""
            if "lng" in row:
                row["lng"] = record.get("lng") or ""
            if "category" in row:
                row["category"] = str(record.get("category") or "").strip()
            if "location_label" in row:
                row["location_label"] = str(record.get("location_label") or "").strip()
            if "source_type" in row:
                row["source_type"] = str(record.get("source_type") or "").strip()
            if "source_note" in row:
                row["source_note"] = str(record.get("source_note") or "").strip()

            row[embedding_col] = embedding
            writer.writerow(row)

    print(
        f"Wrote {len(rows)} rows to {output_path} "
        f"(embedding_dim={dimension}, embedding_col={embedding_col}, format={fmt})"
    )


if __name__ == "__main__":
    main()

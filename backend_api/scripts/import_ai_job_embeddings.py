#!/usr/bin/env python
"""Update job_post.embedding from a CSV with embeddings (match by title)."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

from sqlalchemy import text
from sqlmodel import Session

from backend_api.app.db.database import create_db_and_tables, engine


EMBEDDING_COLUMN_CANDIDATES = ("embedding", "embeddings", "vector", "embedding_vector")
DEFAULT_DIM = 1024


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update job_post.embedding from a CSV")
    parser.add_argument("--csv", type=Path, required=True, help="CSV path with embeddings")
    parser.add_argument("--dim", type=int, default=DEFAULT_DIM, help="Expected embedding dimension")
    return parser.parse_args()


def _find_embedding_column(header: Sequence[str]) -> Optional[str]:
    for name in EMBEDDING_COLUMN_CANDIDATES:
        if name in header:
            return name
    for col in header:
        if "embedding" in col.lower():
            return col
    return None


def _parse_embedding(raw: Optional[str]) -> Optional[list[float]]:
    text = (raw or "").strip()
    if not text:
        return None

    if text.startswith("[") and text.endswith("]"):
        for parser in (json.loads, ast.literal_eval):
            try:
                data = parser(text)
                if isinstance(data, (list, tuple)):
                    return [float(v) for v in data]
            except Exception:
                continue
        return None

    parts = [p for p in re.split(r"[\s,]+", text) if p]
    try:
        return [float(v) for v in parts]
    except Exception:
        return None


def _vector_literal(values: Iterable[float]) -> str:
    return "[" + ", ".join(str(float(v)) for v in values) + "]"


def main() -> None:
    args = _parse_args()
    csv_path = args.csv
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    create_db_and_tables()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if not reader.fieldnames:
            raise SystemExit("CSV header not found")
        embedding_col = _find_embedding_column(reader.fieldnames)
        if not embedding_col:
            raise SystemExit("Embedding column not found in CSV header")

        updated = 0
        skipped = 0
        missing_title = 0
        batch_count = 0
        update_by_id_stmt = text(
            "UPDATE job_post SET embedding = CAST(:vec AS vector) "
            "WHERE (ai_summary->>'csv_job_id') = :csv_job_id"
        )
        update_by_title_stmt = text(
            "UPDATE job_post SET embedding = CAST(:vec AS vector) "
            "WHERE title = :title"
        )

        with Session(engine) as session:
            for row in reader:
                title = (row.get("title") or "").strip()
                if not title:
                    missing_title += 1
                    continue
                csv_job_id = (row.get("job_id") or "").strip()
                vec = _parse_embedding(row.get(embedding_col))
                if not vec:
                    skipped += 1
                    continue
                if args.dim and len(vec) != args.dim:
                    skipped += 1
                    continue
                vec_str = "[" + ",".join(map(str, vec)) + "]"
                result = None
                if csv_job_id:
                    result = session.execute(
                        update_by_id_stmt,
                        {"vec": vec_str, "csv_job_id": csv_job_id},
                    )
                if not result or not getattr(result, "rowcount", 0):
                    result = session.execute(
                        update_by_title_stmt,
                        {"vec": vec_str, "title": title},
                    )
                if getattr(result, "rowcount", 0):
                    updated += result.rowcount
                batch_count += 1
                if batch_count % 50 == 0:
                    session.commit()
            session.commit()

    print(
        f"[import_ai_job_embeddings] Updated {updated} embeddings "
        f"(skipped={skipped}, missing_title={missing_title})"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[import_ai_job_embeddings] failed: {exc}", file=sys.stderr)
        raise

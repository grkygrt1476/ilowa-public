# backend_api/scripts/find_bad_times.py

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "ai_modeling" / "data" / "job_seed_seniorforum.json"

with path.open(encoding="utf-8") as f:
    data = json.load(f)

bad = []

for idx, row in enumerate(data):
    for field in ("start_time", "end_time"):
        val = (row.get(field) or "").strip()
        if not val:
            continue
        times = [t.strip() for t in val.split(",") if t.strip()]
        if len(times) > 1:
            bad.append((idx, field, val))

for idx, field, val in bad:
    print(f"{idx}: {field} = {val}")

print("TOTAL:", len(bad))

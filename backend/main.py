import csv
import os
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CSV_PATH = "/data/violations.csv"
HEADERS = ["id", "person", "word", "amount", "timestamp"]


def ensure_csv():
    os.makedirs("/data", exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writeheader()


def read_all() -> list[dict]:
    ensure_csv()
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_row(row: dict):
    ensure_csv()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=HEADERS).writerow(row)


def delete_row(row_id: str) -> bool:
    rows = read_all()
    new_rows = [r for r in rows if r["id"] != row_id]
    if len(new_rows) == len(rows):
        return False
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        w.writerows(new_rows)
    return True


class ViolationIn(BaseModel):
    person: str
    word: Optional[str] = "---"
    amount: Optional[float] = 1.0


@app.get("/api/violations")
def get_violations():
    return read_all()


@app.post("/api/violations", status_code=201)
def create_violation(data: ViolationIn):
    row = {
        "id": str(uuid.uuid4())[:8],
        "person": data.person.strip(),
        "word": (data.word or "---").strip(),
        "amount": data.amount or 1.0,
        "timestamp": datetime.now().isoformat(),
    }
    append_row(row)
    return row


@app.delete("/api/violations/{violation_id}")
def delete_violation(violation_id: str):
    if not delete_row(violation_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@app.get("/api/stats")
def get_stats():
    rows = read_all()
    total = sum(float(r["amount"]) for r in rows)
    offenders: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for r in rows:
        offenders[r["person"]]["total"] += float(r["amount"])
        offenders[r["person"]]["count"] += 1
    ranked = sorted(
        [{"person": p, **v} for p, v in offenders.items()],
        key=lambda x: x["total"],
        reverse=True,
    )
    return {"total": total, "count": len(rows), "offenders": ranked}

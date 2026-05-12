import os
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def sb_headers() -> dict:
    key = os.environ["SUPABASE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def sb_url(table: str) -> str:
    return f"{os.environ['SUPABASE_URL']}/rest/v1/{table}"


class ViolationIn(BaseModel):
    person: str
    word: Optional[str] = "---"
    amount: Optional[float] = 1.0


@app.get("/api/violations")
def get_violations():
    r = httpx.get(sb_url("violations"), headers=sb_headers(), params={"order": "timestamp.asc"})
    r.raise_for_status()
    return r.json()


@app.post("/api/violations", status_code=201)
def create_violation(data: ViolationIn):
    violation = {
        "id": str(uuid.uuid4())[:8],
        "person": data.person.strip(),
        "word": (data.word or "---").strip(),
        "amount": data.amount or 1.0,
        "timestamp": datetime.now().isoformat(),
    }
    r = httpx.post(sb_url("violations"), headers=sb_headers(), json=violation)
    r.raise_for_status()
    return r.json()[0]


@app.delete("/api/violations/{violation_id}")
def delete_violation(violation_id: str):
    r = httpx.delete(
        sb_url("violations"),
        headers=sb_headers(),
        params={"id": f"eq.{violation_id}"},
    )
    r.raise_for_status()
    if not r.json():
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@app.get("/api/stats")
def get_stats():
    r = httpx.get(sb_url("violations"), headers=sb_headers())
    r.raise_for_status()
    violations = r.json()
    total = sum(float(v["amount"]) for v in violations)
    offenders: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for v in violations:
        offenders[v["person"]]["total"] += float(v["amount"])
        offenders[v["person"]]["count"] += 1
    ranked = sorted(
        [{"person": p, **d} for p, d in offenders.items()],
        key=lambda x: x["total"],
        reverse=True,
    )
    return {"total": total, "count": len(violations), "offenders": ranked}


@app.get("/{path:path}")
def serve_frontend(path: str):
    candidate = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(candidate):
        return FileResponse(candidate)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

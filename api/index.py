import os
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

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


def get_db():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


class ViolationIn(BaseModel):
    person: str
    word: Optional[str] = "---"
    amount: Optional[float] = 1.0


@app.get("/api/violations")
def get_violations():
    db = get_db()
    res = db.table("violations").select("*").order("timestamp", desc=False).execute()
    return res.data


@app.post("/api/violations", status_code=201)
def create_violation(data: ViolationIn):
    db = get_db()
    violation = {
        "id": str(uuid.uuid4())[:8],
        "person": data.person.strip(),
        "word": (data.word or "---").strip(),
        "amount": data.amount or 1.0,
        "timestamp": datetime.now().isoformat(),
    }
    res = db.table("violations").insert(violation).execute()
    return res.data[0]


@app.delete("/api/violations/{violation_id}")
def delete_violation(violation_id: str):
    db = get_db()
    res = db.table("violations").delete().eq("id", violation_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@app.get("/api/stats")
def get_stats():
    db = get_db()
    res = db.table("violations").select("*").execute()
    violations = res.data
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

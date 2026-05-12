import json
import os
import urllib.error
import urllib.request
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


def sb(method: str, table: str, data: dict = None, params: dict = None) -> list:
    key = os.environ["SUPABASE_KEY"]
    base = os.environ["SUPABASE_URL"].rstrip("/")
    url = f"{base}/rest/v1/{table}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail=e.read().decode())


class ViolationIn(BaseModel):
    person: str
    word: Optional[str] = "---"
    amount: Optional[float] = 1.0


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "supabase_url": os.environ.get("SUPABASE_URL", "NOT SET"),
        "key_set": bool(os.environ.get("SUPABASE_KEY")),
    }


@app.get("/api/violations")
def get_violations():
    return sb("GET", "violations", params={"order": "timestamp.asc"})


@app.post("/api/violations", status_code=201)
def create_violation(data: ViolationIn):
    violation = {
        "id": str(uuid.uuid4())[:8],
        "person": data.person.strip(),
        "word": (data.word or "---").strip(),
        "amount": data.amount or 1.0,
        "timestamp": datetime.now().isoformat(),
    }
    result = sb("POST", "violations", data=violation)
    return result[0]


@app.delete("/api/violations/{violation_id}")
def delete_violation(violation_id: str):
    result = sb("DELETE", "violations", params={"id": f"eq.{violation_id}"})
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@app.get("/api/stats")
def get_stats():
    violations = sb("GET", "violations")
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

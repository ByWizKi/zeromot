import json
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

VIOLATIONS_KEY = "zeromot:violations"


def get_redis():
    from upstash_redis import Redis
    return Redis(
        url=os.environ["KV_REST_API_URL"],
        token=os.environ["KV_REST_API_TOKEN"],
    )


def read_violations() -> list[dict]:
    r = get_redis()
    data = r.get(VIOLATIONS_KEY)
    if not data:
        return []
    return json.loads(data) if isinstance(data, str) else data


def write_violations(violations: list[dict]):
    r = get_redis()
    r.set(VIOLATIONS_KEY, json.dumps(violations, ensure_ascii=False))


class ViolationIn(BaseModel):
    person: str
    word: Optional[str] = "---"
    amount: Optional[float] = 1.0


@app.get("/api/violations")
def get_violations():
    return read_violations()


@app.post("/api/violations", status_code=201)
def create_violation(data: ViolationIn):
    violation = {
        "id": str(uuid.uuid4())[:8],
        "person": data.person.strip(),
        "word": (data.word or "---").strip(),
        "amount": data.amount or 1.0,
        "timestamp": datetime.now().isoformat(),
    }
    violations = read_violations()
    violations.append(violation)
    write_violations(violations)
    return violation


@app.delete("/api/violations/{violation_id}")
def delete_violation(violation_id: str):
    violations = read_violations()
    new_list = [v for v in violations if v["id"] != violation_id]
    if len(new_list) == len(violations):
        raise HTTPException(status_code=404, detail="Not found")
    write_violations(new_list)
    return {"ok": True}


@app.get("/api/stats")
def get_stats():
    violations = read_violations()
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
    # Serve static assets (JS, CSS, etc.)
    candidate = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(candidate):
        return FileResponse(candidate)
    # SPA fallback
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

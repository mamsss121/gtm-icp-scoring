"""
Lookalike scorer (Method 1).

Embeds the descriptions of our 10 best customers once at startup, then for any
new company description returns how similar it is to them (0-100) and which
best customer it most resembles. Clay calls POST /score through its HTTP API column.
"""
import json
import os
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Header, HTTPException
from fastembed import TextEmbedding
from pydantic import BaseModel

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, ~90 MB, CPU-friendly
SEED_FILE = Path(__file__).parent / "seed_customers.json"
API_KEY = os.getenv("SCORER_API_KEY")  # optional shared secret sent by Clay as x-api-key

app = FastAPI(title="ICP lookalike scorer")
model = TextEmbedding(MODEL_NAME)

seeds = json.loads(SEED_FILE.read_text())  # [{"name": ..., "description": ...}, ...]
seed_names = [s["name"] for s in seeds]
seed_vecs = np.array(list(model.embed([s["description"] for s in seeds])))
seed_vecs /= np.linalg.norm(seed_vecs, axis=1, keepdims=True)
centroid = seed_vecs.mean(axis=0)
centroid /= np.linalg.norm(centroid)


class ScoreRequest(BaseModel):
    name: str | None = None
    description: str


class ScoreResponse(BaseModel):
    lookalike_score: int          # 0-100, similarity to the average best customer
    max_similarity: int           # 0-100, similarity to the single closest customer
    nearest_customer: str


def to_score(cos: float) -> int:
    # MiniLM cosine for related business texts sits roughly in 0.0-0.8; clip and rescale.
    return int(round(np.clip(cos / 0.8, 0, 1) * 100))


@app.get("/health")
def health():
    return {"ok": True, "seeds": len(seed_names)}


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest, x_api_key: str | None = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="bad api key")
    text = (req.description or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="empty description")
    vec = np.array(list(model.embed([text[:2000]])))[0]
    vec /= np.linalg.norm(vec)
    sims = seed_vecs @ vec
    best = int(np.argmax(sims))
    return ScoreResponse(
        lookalike_score=to_score(float(centroid @ vec)),
        max_similarity=to_score(float(sims[best])),
        nearest_customer=seed_names[best],
    )

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

app = FastAPI(title="clawd_worker", version="0.1.0")


class HuntRequest(BaseModel):
    client_id: str
    source_type: Literal["reddit", "rss", "web"] = "web"
    query: str = ""
    since: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=500)


class LeadItem(BaseModel):
    source_type: str
    source_ref: str
    url: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    text_excerpt: str = ""


class HuntResponse(BaseModel):
    items: List[LeadItem] = []


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/tasks/hunt", response_model=HuntResponse)
def hunt(req: HuntRequest):
    # TODO: implement real scraping/extraction via Browserless/OpenClaw.
    # Return empty for now (safe skeleton).
    return HuntResponse(items=[])

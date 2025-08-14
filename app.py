# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import yaml, os, json, time

from .agent.core import AgenticMiddleware, Event
from .agent.outbox import Outbox
from .agent.logger import log_json
from .infra.tracing import init_tracing
from .infra.approval import Approvals
from .infra.consumer_runner import run_consumer

# Load policies
POLICY_PATH = os.environ.get("POLICY_PATH", os.path.join(os.path.dirname(__file__), "agent/policies.yaml"))
with open(POLICY_PATH, "r") as f:
    POLICIES = yaml.safe_load(f)

# Load config
CFG_PATH = os.environ.get("APP_CONFIG", os.path.join(os.path.dirname(__file__), "../config.example.yaml"))
with open(CFG_PATH, "r") as f:
    APP_CONFIG = yaml.safe_load(f)

# Setup outbox
OUTBOX_PATH = os.environ.get("OUTBOX_PATH", os.path.join(os.path.dirname(__file__), "outbox.sqlite"))

# Init tracing
init_tracing(service_name="agentic-middleware")

agent = AgenticMiddleware(policies=POLICIES, outbox=Outbox(OUTBOX_PATH), config=APP_CONFIG)

class EventIn(BaseModel):
    id: str
    source: str
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None

class ApprovalIn(BaseModel):
    trace_id: str
    step_name: str
    approved_by: Optional[str] = "unknown"

app = FastAPI(title="Agentic AI Middleware")

@app.get("/health")
def health():
    return {"status": "ok", "time": int(time.time())}

@app.post("/ingest")
def ingest(event: EventIn):
    try:
        ev = Event(**event.model_dump())
        result = agent.handle_event(ev)
        return {"ok": True, "result": result}
    except Exception as e:
        log_json(level="error", msg="ingest_failed", error=str(e), event_id=event.id, etype=event.type)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approve")
def approve(payload: ApprovalIn):
    try:
        agent.approvals.approve(payload.trace_id, payload.step_name, user=payload.approved_by or "unknown")
        return {"ok": True, "approved": {"trace_id": payload.trace_id, "step": payload.step_name}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/consume/start")
def consume_start(group_id: str = "agentic-consumer", topic: str = "orders.created"):
    try:
        # Non-blocking start
        import threading
        t = threading.Thread(target=run_consumer, args=(agent, group_id, [topic]), daemon=True)
        t.start()
        return {"ok": True, "status": "started", "group_id": group_id, "topic": topic}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

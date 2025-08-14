# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

from typing import Any, Dict, Callable
import json, requests, os
from .logger import log_json
from ..infra.kafka import get_producer
from ..infra.secret import SecretProvider, auth_header_from_spec

# Registry
_TOOL_REGISTRY = {}
_SECRET_PROVIDER = None
_SERVICE_CFG = {}

def init_tools(config: dict):
    global _SECRET_PROVIDER, _SERVICE_CFG
    _SERVICE_CFG = config.get("services", {})
    _SECRET_PROVIDER = SecretProvider(config.get("secrets", {}))

def tool(name: str):
    def deco(fn: Callable):
        _TOOL_REGISTRY[name] = fn
        return fn
    return deco

def run_tool(name: str, params: Dict[str, Any], ctx, is_compensation: bool=False) -> Dict[str, Any]:
    if name not in _TOOL_REGISTRY:
        raise RuntimeError(f"Unknown tool: {name}")
    # Guardrails (RBAC/domain)
    allow = ctx.policies.get("rbac", {}).get("roles", {}).get("agent", {}).get("allow_tools", [])
    if name not in allow:
        raise PermissionError(f"Tool not allowed by RBAC: {name}")
    res = _TOOL_REGISTRY[name](params, ctx, is_compensation)
    return res

def _base_url(service_key: str, default: str=""):
    svc = _SERVICE_CFG.get(service_key, {})
    return svc.get("base_url", default)

def _auth_for(service_key: str):
    svc = _SERVICE_CFG.get(service_key, {})
    spec = svc.get("auth")  # e.g., "bearer:CRM_TOKEN"
    if not spec or _SECRET_PROVIDER is None:
        return {}
    return auth_header_from_spec(spec, _SECRET_PROVIDER)

@tool("publish_kafka")
def publish_kafka(params, ctx, is_compensation=False):
    topic = params.get("topic", "default")
    prod = get_producer()
    payload = json.dumps({"trace_id": ctx.event.trace_id, "event": ctx.event.payload})
    if prod is None:
        offset = ctx.outbox.next_offset(topic)
        log_json(level="info", msg="publish_kafka_stub", topic=topic, offset=offset, fallback=True)
        return {"offset": offset, "topic": topic, "fallback": True}
    try:
        # Try confluent first
        if hasattr(prod, "produce"):
            prod.produce(topic, payload.encode("utf-8"))
            prod.flush()
            log_json(level="info", msg="publish_kafka", topic=topic, fallback=False)
            return {"offset": None, "topic": topic}
        # kafka-python
        elif hasattr(prod, "send"):
            prod.send(topic, payload)
            prod.flush()
            log_json(level="info", msg="publish_kafka", topic=topic, fallback=False)
            return {"offset": None, "topic": topic}
    except Exception as e:
        log_json(level="error", msg="publish_kafka_fail", topic=topic, error=str(e))
        # Fallback to outbox offset
        offset = ctx.outbox.next_offset(topic)
        return {"offset": offset, "topic": topic, "fallback": True}

@tool("call_rest")
def call_rest(params, ctx, is_compensation=False):
    url = params.get("url")
    method = params.get("method", "GET").upper()
    body = params.get("body")
    headers = {"x-trace-id": ctx.event.trace_id, **ctx.event.headers}

    # Route based on prefix keys: /crm/*, /wms/* else absolute
    if url.startswith("/crm/"):
        base = _base_url("crm", "https://httpbin.org")
        headers |= _auth_for("crm")
    elif url.startswith("/wms/"):
        base = _base_url("wms", "https://httpbin.org")
        headers |= _auth_for("wms")
    else:
        base = ""
    full = base + url if url.startswith("/") else url

    try:
        resp = requests.request(method, full, json=body, headers=headers, timeout=5)
        ctype = resp.headers.get("content-type","")
        return {"status": resp.status_code, "json": resp.json() if "application/json" in ctype else None}
    except Exception as e:
        raise RuntimeError(f"http_error: {e}")

@tool("transform_json")
def transform_json(params, ctx, is_compensation=False):
    fn = params.get("template_or_fn")
    data = {"event": ctx.event.payload, "prior": ctx.results}
    if fn == "merge_customer":
        cust = ctx.results.get("fetch_customer", {}).get("json", {}) if ctx.results else {}
        merged = {**ctx.event.payload, **{"customer": cust}}
        return {"data": merged}
    return {"data": data}

@tool("open_ticket")
def open_ticket(params, ctx, is_compensation=False):
    # Potentially gated by approval (human-in-the-loop)
    priority = params.get("priority", "P1")
    requires_approval = priority == "P0"
    if requires_approval:
        from ..infra.approval import Approvals
        approvals = ctx.approvals  # injected
        if not approvals.is_approved(ctx.event.trace_id, ctx.current_step_name):
            # Pause execution by raising a special error that the executor will surface
            raise RuntimeError("approval_required")
    details = {"title": params.get("title", "Agentic incident"),
               "priority": priority,
               "trace_id": ctx.event.trace_id,
               "event_id": ctx.event.id}
    log_json(level="warning", msg="ticket_opened", details=details, compensation=is_compensation)
    return {"ticket_id": f"T-{ctx.outbox.next_offset('tickets')}"}


@tool("route_jms")
def route_jms(params, ctx, is_compensation=False):
    """Stub for routing to a JMS destination (e.g., TIBCO EMS queue/topic).
    Configure a real EMS producer in production and call it here.
    params: { "destination": "queue/Topic.Name", "payload": {...} }
    """
    dest = params.get("destination", "QUEUE.DEFAULT")
    payload = params.get("payload", {"trace_id": ctx.event.trace_id, "event": ctx.event.payload})
    # In real use: send via a JMS client/bridge (e.g., Java microservice, BW process, or REST gateway)
    msg_id = f"jms-{ctx.outbox.next_offset('jms:'+dest)}"
    log_json(level="info", msg="route_jms_stub", destination=dest, message_id=msg_id, compensation=is_compensation)
    return {"destination": dest, "message_id": msg_id}

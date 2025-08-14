# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

from typing import Any, Dict, List
from .core import Plan

def infer_intents(obs: Dict[str, Any], ctx) -> List[str]:
    # Deterministic fast-path
    etype = obs.get("type")
    payload = obs.get("payload", {})
    region = payload.get("region") or payload.get("Region")

    if etype == "ORDER_CREATED" and region in ("US", "EU"):
        return ["enrich_order", "reserve_inventory", "notify_oms"]

    # Retrieval & LLM hooks could go here (omitted; see README)
    return ["notify_oms"]

def build_plan(intents: List[str], ctx) -> Plan:
    plan = Plan()
    if "enrich_order" in intents:
        plan.add_step("fetch_customer", tool="call_rest", params={"url": "/crm/customer", "method": "GET"})
        plan.add_step("merge_profile", tool="transform_json", depends_on=["fetch_customer"],
                      params={"template_or_fn": "merge_customer"})
    if "reserve_inventory" in intents:
        plan.add_step("reserve", tool="call_rest",
                      params={"url": "/wms/reservations", "method": "POST"},
                      depends_on=["merge_profile"])
        plan.add_compensation("reserve", tool="call_rest",
                              params={"url": "/wms/cancel_reservation", "method": "POST"})
    if "notify_oms" in intents:
        plan.add_step("publish", tool="publish_kafka",
                      params={"topic": "oms.events"},
                      depends_on=["reserve"] if "reserve_inventory" in intents else [])
    return plan

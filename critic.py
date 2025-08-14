# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

from typing import Any, Dict
from .logger import log_json

def critic_ok(step, res: Dict[str, Any], ctx) -> bool:
    # Basic checks; extend per tool type & SLOs
    if step.tool == "call_rest":
        if not isinstance(res, dict) or res.get("status", 500) >= 500:
            log_json(level="error", msg="critic_http_fail", step=step.name, status=res.get("status"))
            return False
    if step.tool == "publish_kafka":
        if res.get("offset") is None:
            log_json(level="error", msg="critic_publish_fail", step=step.name)
            return False
    max_latency = ctx.policies.get("slo", {}).get("max_latency_ms")
    if max_latency and ctx.latency_ms() > max_latency:
        log_json(level="error", msg="critic_latency", step=step.name, latency=int(ctx.latency_ms()))
        return False
    return True

def recover(failed_step, ctx):
    # Run compensations for completed steps
    for s in reversed(ctx.completed_steps):
        if s.compensation:
            comp = s.compensation
            try:
                from .tools import run_tool
                run_tool(comp["tool"], comp.get("params", {}), ctx, is_compensation=True)
                log_json(level="warning", msg="compensation_ok", step=s.name)
            except Exception as e:
                log_json(level="error", msg="compensation_failed", step=s.name, error=str(e))

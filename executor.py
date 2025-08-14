# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

import time, random
from typing import Any, Dict
from .tools import run_tool
from .logger import log_json

def _exp_backoff(base_ms: int, attempt: int, max_ms: int) -> float:
    return min(max_ms, base_ms * (2 ** (attempt - 1))) / 1000.0

class Executor:
    def __init__(self, policies: Dict[str, Any], outbox, approvals=None):
        self.policies = policies
        self.outbox = outbox
        self.approvals = approvals

    def execute_step(self, step, ctx):
        # Idempotency (Outbox check)
        idem_key = f"{ctx.event.id}:{step.name}"
        saved = self.outbox.get(idem_key)
        if saved is not None:
            log_json(level="info", msg="idempotent_reuse", step=step.name, key=idem_key)
            return saved

        retry_cfg = self.policies.get("execution", {}).get("retry", {})
        base_ms = int(retry_cfg.get("base_ms", 100))
        max_ms = int(retry_cfg.get("max_ms", 1000))
        max_retries = int(self.policies.get("slo", {}).get("max_retries", 2))

        attempt = 0
        while True:
            attempt += 1
            try:
                # Attach approvals & current step for tools needing it
                ctx.approvals = self.approvals
                ctx.current_step_name = step.name
                res = run_tool(step.tool, step.params, ctx)
                self.outbox.put(idem_key, res)
                log_json(level="info", msg="step_ok", step=step.name)
                return res
            except Exception as e:
                if "approval_required" in str(e):
                    log_json(level="warning", msg="step_waiting_approval", step=step.name)
                    raise
                log_json(level="warning", msg="step_retry", step=step.name, attempt=attempt, error=str(e))
                if attempt > max_retries:
                    log_json(level="error", msg="step_failed", step=step.name, error=str(e))
                    raise
                time.sleep(_exp_backoff(base_ms, attempt, max_ms) + random.random() * 0.05)

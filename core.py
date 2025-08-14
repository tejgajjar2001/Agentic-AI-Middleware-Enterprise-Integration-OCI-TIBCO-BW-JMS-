# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time, uuid

from .planner import infer_intents, build_plan
from .executor import Executor
from .critic import critic_ok, recover
from .logger import log_json
from ..infra.tracing import get_tracer
from ..infra.approval import Approvals
from .sanitizer import configure as sanitize_config
from .tools import init_tools

@dataclass
class Event:
    id: str
    source: str
    type: str
    payload: Dict[str, Any]
    headers: Dict[str, Any]
    trace_id: Optional[str] = None

@dataclass
class PlanStep:
    name: str
    tool: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    compensation: Optional[Dict[str, Any]] = None

@dataclass
class Plan:
    steps: Dict[str, PlanStep] = field(default_factory=dict)

    def add_step(self, name: str, tool: str, params: Dict[str, Any] = None, depends_on=None):
        self.steps[name] = PlanStep(name=name, tool=tool, params=params or {}, depends_on=depends_on or [])
        return self

    def add_compensation(self, step_name: str, tool: str, params: Dict[str, Any] = None):
        self.steps[step_name].compensation = {"tool": tool, "params": params or {}}

    def topo_order(self) -> List[PlanStep]:
        incoming = {n: set(s.depends_on) for n, s in self.steps.items()}
        order = []
        while True:
            free = [n for n, deps in incoming.items() if len(deps) == 0]
            if not free:
                break
            for n in free:
                order.append(self.steps[n])
                del incoming[n]
                for m in incoming:
                    incoming[m].discard(n)
        if incoming:
            raise RuntimeError("Cyclic or unresolved dependencies in plan")
        return order

class Context:
    def __init__(self, event: Event, policies: Dict[str, Any], outbox, approvals: Approvals):
        self.event = event
        self.policies = policies
        self.outbox = outbox
        self.approvals = approvals
        self.started_ms = time.time() * 1000.0
        self.completed_steps: List[PlanStep] = []
        self.results: Dict[str, Any] = {}
        self.current_step_name: str = ""

    def latency_ms(self) -> float:
        return (time.time() * 1000.0) - self.started_ms

class AgenticMiddleware:
    def __init__(self, policies: Dict[str, Any], outbox, config: Dict[str, Any] | None = None):
        self.policies = policies
        self.approvals = Approvals()
        self.executor = Executor(policies=policies, outbox=outbox, approvals=self.approvals)
        # Configure sanitizer and tools with config
        sanitize_config(policies)
        init_tools(config or {})

    def _init_context(self, event: Event) -> Context:
        if not event.trace_id:
            event.trace_id = str(uuid.uuid4())
        return Context(event, self.policies, self.executor.outbox, self.approvals)

    def handle_event(self, event: Event) -> Dict[str, Any]:
        tracer = get_tracer("agent.handle_event")
        ctx = self._init_context(event)

        with tracer.start_as_current_span("sense"):
            log_json(level="info", msg="sense", trace_id=event.trace_id, etype=event.type, eid=event.id)
            obs = {"type": event.type, "payload": event.payload, "headers": event.headers}

        with tracer.start_as_current_span("think_plan"):
            intents = infer_intents(obs, ctx)
            plan = build_plan(intents, ctx)

        slo = ctx.policies.get("slo", {})
        if slo.get("max_steps") and len(plan.steps) > slo["max_steps"]:
            raise RuntimeError("Plan exceeds max_steps policy")

        results = {}
        for step in plan.topo_order():
            with tracer.start_as_current_span(f"act.{step.name}"):
                try:
                    res = self.executor.execute_step(step, ctx)
                    results[step.name] = res
                    ctx.completed_steps.append(step)
                    ctx.results[step.name] = res
                    if not critic_ok(step, res, ctx):
                        raise RuntimeError("critic_reject")
                except Exception as e:
                    recover(step, ctx)
                    log_json(level="error", msg="plan_failed", step=step.name, trace_id=event.trace_id, error=str(e))
                    return {"status": "failed", "trace_id": event.trace_id, "partial": results, "failed_step": step.name}

        log_json(level="info", msg="plan_success", trace_id=event.trace_id)
        return {"status": "ok", "trace_id": event.trace_id, "results": results}

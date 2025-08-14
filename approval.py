# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

from typing import Dict, Set

class Approvals:
    def __init__(self):
        self._store: Dict[str, Set[str]] = {}

    def require_key(self, trace_id: str, step_name: str) -> str:
        return f"{trace_id}:{step_name}"

    def approve(self, trace_id: str, step_name: str, user: str = "unknown"):
        key = self.require_key(trace_id, step_name)
        s = self._store.get(key, set())
        s.add(user)
        self._store[key] = s
        return True

    def is_approved(self, trace_id: str, step_name: str) -> bool:
        key = self.require_key(trace_id, step_name)
        return key in self._store and len(self._store[key]) > 0

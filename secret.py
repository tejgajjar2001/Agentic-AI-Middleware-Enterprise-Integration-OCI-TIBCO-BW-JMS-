# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

import os, json
from typing import Optional

class SecretProvider:
    def __init__(self, config: dict | None = None):
        self.cfg = config or {}

    def get(self, name: str) -> Optional[str]:
        # Priority: ENV > file > static map
        val = os.environ.get(name)
        if val:
            return val
        files = self.cfg.get("files", {})
        path = files.get(name)
        if path and os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
        static = self.cfg.get("static", {})
        return static.get(name)

# Helpers to build Authorization headers from config like "bearer:CRM_TOKEN"
def auth_header_from_spec(spec: str, sp: SecretProvider) -> dict:
    if not spec:
        return {}
    try:
        kind, key = spec.split(":", 1)
    except ValueError:
        return {}
    secret = sp.get(key)
    if not secret:
        return {}
    if kind == "bearer":
        return {"Authorization": f"Bearer {secret}"}
    if kind == "basic":
        return {"Authorization": f"Basic {secret}"}
    return {}

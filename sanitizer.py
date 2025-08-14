# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

from typing import Any, Dict, Set, List

_REDACT_FIELDS: Set[str] = set(["ssn","card_number","dob","email","password","token","secret","api_key"])

def configure(policies: Dict[str, Any]):
    global _REDACT_FIELDS
    dp = policies.get("data_policy", {})
    rf = dp.get("redact_fields", [])
    if isinstance(rf, list):
        _REDACT_FIELDS = set([str(x) for x in rf])

def _sanitize_obj(o):
    if isinstance(o, dict):
        return {k: ("***" if str(k).lower() in _REDACT_FIELDS else _sanitize_obj(v)) for k, v in o.items()}
    elif isinstance(o, list):
        return [_sanitize_obj(x) for x in o]
    else:
        return o

def sanitize(o):
    try:
        return _sanitize_obj(o)
    except Exception:
        return o

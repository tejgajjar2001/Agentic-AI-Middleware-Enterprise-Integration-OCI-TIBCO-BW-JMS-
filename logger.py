# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

import json, sys, time
from .sanitizer import sanitize

def log_json(**kwargs):
    rec = {"ts": int(time.time()*1000)}
    rec.update(kwargs)
    safe = sanitize(rec)
    sys.stdout.write(json.dumps(safe) + "\n")
    sys.stdout.flush()

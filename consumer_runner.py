# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

import json, threading, time
from ..agent.core import AgenticMiddleware, Event
from .kafka import get_consumer

def run_consumer(agent: AgenticMiddleware, group_id: str, topics: list[str]):
    cinfo = get_consumer(group_id, topics)
    if not cinfo:
        print("Kafka bootstrap not configured or client unavailable; consumer not started.")
        return
    kind, c = cinfo
    print(f"Kafka consumer started ({kind}) on topics: {topics}")
    if kind == "confluent":
        while True:
            msg = c.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print("Consumer error:", msg.error())
                continue
            try:
                data = json.loads(msg.value().decode("utf-8"))
                ev = Event(**data)
                agent.handle_event(ev)
            except Exception as e:
                print("Handle error:", e)
    else:
        for m in c:
            try:
                data = json.loads(m.value.decode("utf-8"))
                ev = Event(**data)
                agent.handle_event(ev)
            except Exception as e:
                print("Handle error:", e)

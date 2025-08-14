# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

import os
from typing import Optional

_producer = None
_consumer = None

def _get_bootstrap_env():
    # Prefer explicit OCI env, fallback to generic Kafka env
    return os.environ.get("OCI_STREAMING_BOOTSTRAP") or os.environ.get("KAFKA_BOOTSTRAP_SERVERS")

def _sasl_conf():
    mech = os.environ.get("SASL_MECHANISM", "PLAIN")
    user = os.environ.get("SASL_USERNAME")
    pw = os.environ.get("SASL_PASSWORD")
    proto = os.environ.get("SECURITY_PROTOCOL", "SASL_SSL" if (user and pw) else "PLAINTEXT")
    ca = os.environ.get("SSL_CA_LOCATION")  # optional
    return mech, user, pw, proto, ca


def get_bootstrap():
    return _get_bootstrap_env()

def get_producer():
    global _producer
    if _producer is not None:
        return _producer
    bs = get_bootstrap()
    if not bs:
        return None
    try:
        from confluent_kafka import Producer
        conf = {
            "bootstrap.servers": bs,
            "enable.idempotence": True,
            "acks": "all"
        }
        mech, user, pw, proto, ca = _sasl_conf()
        if user and pw:
            conf.update({"security.protocol": proto, "sasl.mechanisms": mech, "sasl.username": user, "sasl.password": pw})
        if ca:
            conf.update({"ssl.ca.location": ca})
        _producer = Producer(conf)
        return _producer
    except Exception:
        try:
            from kafka import KafkaProducer
            _producer = KafkaProducer(bootstrap_servers=bs.split(","), value_serializer=lambda v: v.encode("utf-8"))
            return _producer
        except Exception:
            return None

def get_consumer(group_id: str, topics: list[str]):
    bs = get_bootstrap()
    if not bs:
        return None
    try:
        from confluent_kafka import Consumer
        conf = {"bootstrap.servers": bs, "group.id": group_id, "auto.offset.reset": "earliest"}
        c = Consumer(conf)
        c.subscribe(topics)
        return ("confluent", c)
    except Exception:
        try:
            from kafka import KafkaConsumer
            c = KafkaConsumer(*topics, bootstrap_servers=bs.split(","), group_id=group_id, auto_offset_reset="earliest")
            return ("kafka", c)
        except Exception:
            return None

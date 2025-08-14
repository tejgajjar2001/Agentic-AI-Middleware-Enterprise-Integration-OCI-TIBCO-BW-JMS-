**Agentic AI Middleware — Enterprise Integration (OCI + TIBCO BW/JMS)**

Owner: Tejas Gajjar • © 2025 All rights reserved
Stack: FastAPI · Agentic loop (Sense→Think→Plan→Act→Learn) · OpenTelemetry · Kafka/OCI Streaming · TIBCO BW/JMS · Idempotent Outbox · Policy Guardrails

Production-minded agentic middleware that orchestrates enterprise events across hybrid clouds. It blends deterministic planning with tool skills, hard guardrails (RBAC, SLOs, data policy), saga-style compensations, and first-class observability.

**Features**
Agentic Loop — Sense → Think → Plan → Act → Learn

Deterministic-first planner, retrieval/LLM hook-ready

DAG execution with dependencies & compensations

**Safety & Policy
**
SLOs (latency/retries), RBAC tool allowlists

Data policy with PII redaction in logs

Human-in-the-loop approvals for high-impact steps (P0)

**Reliability**

Idempotent Transactional Outbox (SQLite in dev)

Retries with exponential backoff; saga-style rollback

**Observability**

OpenTelemetry spans for plan/steps/tools

Structured JSON logs with masking

Streaming & Legacy Bridges

Kafka-compatible OCI Streaming (SASL/SSL ready)

route_jms tool for TIBCO BW/EMS integration (stub, replace with EMS publisher in prod)

**Quick Start**
**1) Setup**
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

**2) (Optional) Observability and Streaming**
# OpenTelemetry (e.g., local OTEL Collector)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# OCI Streaming / Kafka-compatible
export OCI_STREAMING_BOOTSTRAP=<host:port,...>
export SASL_USERNAME=<oci-user-or-token-user>
export SASL_PASSWORD=<oci-auth-token>
export SECURITY_PROTOCOL=SASL_SSL
export SASL_MECHANISM=PLAIN
# Optional CA path: export SSL_CA_LOCATION=/etc/ssl/certs/ca-certificates.crt

**3) (Optional) Service Tokens**
export CRM_TOKEN=dev-crm-token
export WMS_TOKEN=dev-wms-token

**4) Run the API**
uvicorn agentic_middleware.app:app --reload --port 8080

**5) Test an Event**
curl -X POST http://localhost:8080/ingest -H "content-type: application/json" -d '{
  "id": "evt-001",
  "source": "orders",
  "type": "ORDER_CREATED",
  "payload": {"orderId":"A123","customerId":"C9","region":"US"},
  "headers": {"x-tenant":"us-retail"},
  "trace_id": "trace-001"
}'

**6) Start a Kafka/OCI Consumer (optional)**
curl -X POST "http://localhost:8080/consume/start?group_id=agentic-consumer&topic=orders.created"

7) Human Approval (when required)
curl -X POST http://localhost:8080/approve -H "content-type: application/json" -d '{
  "trace_id": "trace-001", "step_name": "open_ticket", "approved_by": "oncall"
}'

**Configuration**

**Project reads two configs:**

**Policies:** agentic_middleware/agent/policies.yaml (SLOs, RBAC, data policy, approvals)

**App Config: **config.example.yaml (service base URLs, streaming, secrets)

**Example config.example.yaml:**

service:
  port: 8080
  log_level: INFO

storage:
  outbox_path: "./agentic_middleware/outbox.sqlite"

telemetry:
  otlp_endpoint: "http://localhost:4318"

services:
  crm:
    base_url: "https://your-crm.example.com"
    auth: "bearer:CRM_TOKEN"
  wms:
    base_url: "https://your-wms.example.com"
    auth: "bearer:WMS_TOKEN"
  oms:
    topic: "oms.events"

**integrations:**
  jms:
    default_destination: "QUEUE.ORDERS"   # TIBCO EMS/BW bridge target
  streaming:
    oms_topic: "oms.events"               # Kafka/OCI topic used by publish_kafka

secrets:
  files: {}   # e.g., { "CRM_TOKEN": "/run/secrets/crm_token" }
  static: {}  # e.g., { "CRM_TOKEN": "dev-token" }


**Key Policy Flags (policies.yaml):**

slo.max_latency_ms, slo.max_retries, slo.max_steps

rbac.roles.agent.allow_tools (e.g., publish_kafka, call_rest, transform_json, open_ticket, route_jms)

data_policy.redact_fields (PII fields masked in logs)

API Endpoints

GET /health — health probe

POST /ingest — ingest an event (see example above)

POST /consume/start?group_id=<id>&topic=<topic> — start Kafka/OCI consumer (non-blocking)

POST /approve — human approval gate

{ "trace_id": "trace-001", "step_name": "open_ticket", "approved_by": "oncall" }

Architecture

Loop: Sense → Think → Plan → Act → Learn

Planner (agent/planner.py): deterministic intent inference (fast path), retrieval/LLM hooks ready.

Plan: DAG with explicit dependencies and optional compensations.

Executor (agent/executor.py): retries + backoff; idempotency via Outbox; circuit-break hooks; approval awareness.

Critic (agent/critic.py): validates outputs (HTTP status, publish offsets), checks SLOs; triggers compensation + escalation on failure.

Tools (agent/tools.py):

publish_kafka → Kafka/OCI Streaming (graceful stub fallback)

call_rest → CRM/WMS/… base URLs + auth via secrets

transform_json → small transform library (extend as needed)

open_ticket → approval-gated P0; emits ticket events

route_jms → TIBCO BW/EMS destination (stub; replace with EMS publisher bridge)

Outbox (agent/outbox.py): ensures exactly-once behavior for steps/publications.

Telemetry (infra/tracing.py): OTLP exporter; spans per phase & step.

Approvals (infra/approval.py): in-memory approval store/keying by trace+step.

Kafka/OCI (infra/kafka.py): Confluent or kafka-python with SASL/SSL for OCI Streaming.

Secrets (infra/secret.py): ENV/file/static map; builds Authorization headers.

Project Structure
agentic_middleware/
  app.py                       # FastAPI entrypoint (ingest/approve/consume)
  agent/
    core.py                    # Agent, Plan, Context
    planner.py                 # Intent inference + plan builder
    executor.py                # Step execution, retries, idempotency
    critic.py                  # Output/SLO checks + recovery trigger
    tools.py                   # Tool registry & implementations
    outbox.py                  # SQLite outbox & offsets
    logger.py                  # Structured logging with redaction
    sanitizer.py               # PII redaction
    policies.yaml              # SLO/RBAC/data policy config
  infra/
    tracing.py                 # OpenTelemetry setup
    kafka.py                   # Kafka/OCI Streaming clients (SASL/SSL)
    approval.py                # Human-in-the-loop approvals
    consumer_runner.py         # Long-running consumer loop
    secret.py                  # Secret provider (env/file/static)
config.example.yaml            # App config (services, topics, secrets)
requirements.txt               # Python deps
Dockerfile                     # Container build
README.md                      # This file

Deployment
Docker
docker build -t agentic-middleware:latest .
docker run --rm -p 8080:8080 \
  -e APP_CONFIG=/app/config.example.yaml \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 \
  -e OCI_STREAMING_BOOTSTRAP=broker:9092 \
  -e SASL_USERNAME=oci-user -e SASL_PASSWORD=token \
  -e SECURITY_PROTOCOL=SASL_SSL -e SASL_MECHANISM=PLAIN \
  agentic-middleware:latest

Kubernetes (sketch)

Deploy as a Deployment with config via ConfigMap + secrets via Secret.

Expose as Service (ClusterIP) and secure ingress with your API gateway.

Sidecar the OTEL Collector or export to your centralized collector.

Extending the System

Add a new tool: implement a function in agent/tools.py, decorate with @tool("name"), add to RBAC allowlist.

Add a new intent: update infer_intents and wire steps in build_plan.

Real EMS publishing: replace route_jms stub with a REST/bridge client that posts to an EMS publisher service (or BW microservice).

Security

Redaction: All logs pass through a sanitizer using data_policy.redact_fields.

Secrets: Never hard-code; use ENV or file-mounted secrets and the SecretProvider.

RBAC: Tools must be explicitly allow-listed in policies.yaml.

Approvals: High-impact steps (e.g., P0 tickets) are blocked until /approve is called.

Security contact: tejas.gajjar@macys.com • tejgajjar2001@gmail.com

Ownership & License

© 2025 Tejas Gajjar. All rights reserved.
This repository is proprietary. Please contact the owner for licensing or usage inquiries.

Roadmap

Replace route_jms with production EMS publisher

Domain topic maps & DLQs (OMS/WMS/CRM)

Policy engine (OPA) integration

Retrieval-augmented planner & fix-pattern learning loop

Blue/green rollout of tool skill versions

GitHub Topics

agentic-ai · middleware · enterprise-integration · platform-engineering · oci-streaming · kafka · tibco · jms · fastapi · opentelemetry · saga · idempotency

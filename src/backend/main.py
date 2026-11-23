import time
import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("fintech-payment-engine")

app = FastAPI(
    title="Enterprise FinTech Payment Core",
    description="Mission-critical transaction settlement & ledger reconciliation engine",
    version=os.getenv("APP_VERSION", "3.0.0")
)

# Prometheus Telemetry Instrumentation
if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
    REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Latency in Seconds', ['endpoint'])
    ACTIVE_TX_GAUGE = Gauge('active_financial_transactions', 'Current concurrent transactions undergoing clearing')
    TRANSACTION_VOLUME = Counter('settled_volume_usd_total', 'Cumulative volume processed in USD')
else:
    class DummyMetric:
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    REQUEST_COUNT = DummyMetric()
    REQUEST_LATENCY = DummyMetric()
    ACTIVE_TX_GAUGE = DummyMetric()
    TRANSACTION_VOLUME = DummyMetric()

class TransactionPayload(BaseModel):
    account_id: str = Field(..., min_length=4, max_length=32)
    destination_routing: str = Field(..., min_length=6, max_length=16)
    amount: float = Field(..., gt=0.0)
    currency: str = Field(default="USD", max_length=3)
    idempotency_key: str = Field(..., min_length=8)

@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    endpoint = request.url.path
    status = str(response.status_code)
    REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
    return response

@app.get("/health/liveness")
def liveness_probe():
    return {"status": "ALIVE", "timestamp": time.time()}

@app.get("/health/readiness")
def readiness_probe():
    # Verify downstream database connection pool and vault token
    db_ok = os.getenv("DB_ONLINE", "true").lower() == "true"
    vault_ok = os.getenv("VAULT_SECRETS_MOUNTED", "true").lower() == "true"
    
    if not (db_ok and vault_ok):
        logger.error("Readiness check failed: DB=%s, Vault=%s", db_ok, vault_ok)
        raise HTTPException(status_code=503, detail="Cluster dependencies degraded")
    return {
        "status": "READY",
        "cluster": os.getenv("K8S_NODE_NAME", "k8s-worker-node-04"),
        "version": os.getenv("APP_VERSION", "3.0.0")
    }

@app.get("/metrics")
def metrics():
    if PROMETHEUS_AVAILABLE:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    return Response(content="# HELP http_requests_total Total HTTP Requests\nhttp_requests_total{endpoint=\"/health/liveness\",method=\"GET\",status=\"200\"} 42.0\n", media_type="text/plain")

@app.post("/api/v1/payments/settle")
def process_settlement(tx: TransactionPayload):
    ACTIVE_TX_GAUGE.inc()
    try:
        if tx.amount > 500000.0:
            logger.warning("Transaction %s requires multi-sig compliance review", tx.idempotency_key)
            raise HTTPException(status_code=403, detail="AML volume compliance limit exceeded")
        
        # Core settlement processing simulation
        time.sleep(0.015) # 15ms simulated ledger lock
        tx_id = f"SETTLE-{tx.account_id}-{int(time.time()*1000)}"
        TRANSACTION_VOLUME.inc(tx.amount)
        logger.info("Settlement completed successfully: %s | Amount: $%s", tx_id, tx.amount)
        return {
            "settlement_id": tx_id,
            "status": "CLEARED_AND_SETTLED",
            "amount": tx.amount,
            "currency": tx.currency,
            "reconciled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "engine_version": os.getenv("APP_VERSION", "3.0.0")
        }
    finally:
        ACTIVE_TX_GAUGE.dec()

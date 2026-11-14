"""FastAPI read-only business API. NOT production-authenticated; bind localhost in development."""
from __future__ import annotations
import json
import logging
import sqlite3
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uuid import uuid4
import os
from pydantic import BaseModel, Field, ConfigDict, field_validator
from retailmind.settings import DB, REPORTS
from retailmind import warehouse
from retailmind.agent import investigate, service_status
from retailmind import retrieval
from retailmind.diagnostics import log_failure

logger = logging.getLogger(__name__)

app = FastAPI(title="RetailMind AI", version="0.3.0", description="Synthetic retail analytics and governed AI")

# Explicit local development origins; reverse proxy serves same-origin in Docker.
allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if os.getenv("RETAILMIND_EXTRA_CORS_ORIGIN"):
    allowed_origins.append(os.environ["RETAILMIND_EXTRA_CORS_ORIGIN"])
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"], expose_headers=["X-Correlation-ID"])


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=2000)
    use_langgraph: bool = False

    @field_validator("question")
    @classmethod
    def valid_question(cls, value: str) -> str:
        if not value.strip() or any(ord(c) < 32 and c not in '\n\t\r' for c in value):
            raise ValueError("Question vide ou caractères de contrôle interdits")
        return value.strip()


class TransactionFeatures(BaseModel):
    quantity: int = Field(gt=0, le=1000000)
    unit_price: float = Field(gt=0)
    discount_pct: float = Field(ge=0, le=1)
    total_amount: float = Field(ge=0)
    category: str
    region: str
    channel: str
    payment_status: str


def _ready():
    if not DB.exists():
        raise HTTPException(status_code=503, detail="Warehouse not initialized. Run retailmind bootstrap")


@app.get("/health")
def health():
    return {"service": "retailmind-api", "warehouse_ready": DB.exists(), "data_type": "synthetic"}


@app.get("/ready")
def ready():
    _ready()
    return {"ready": True}


@app.get("/metrics")
def metrics():
    _ready()
    summary = warehouse.execute_readonly("SELECT COUNT(*) AS orders, ROUND(SUM(total_amount),2) AS order_value_mad, "
                                         "ROUND(SUM(CASE WHEN payment_status='paid' THEN total_amount ELSE 0 END),2) AS revenue_mad, "
                                         "SUM(is_anomaly) AS injected_anomalies FROM transactions")
    regions = warehouse.execute_readonly("SELECT region, orders, revenue, injected_anomalies FROM region_metrics "
                                         "ORDER BY revenue DESC")
    return {"summary": summary[0] if summary else {}, "by_region": regions,
            "warning": "Anomalies are synthetic injected labels, not confirmed real-world fraud."}


@app.get("/transactions")
def transactions(limit: int = Query(default=25, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    _ready()
    return warehouse.execute_readonly(
        "SELECT transaction_id, day, region, category, total_amount, payment_status, is_anomaly, anomaly_type "
        "FROM transactions ORDER BY event_timestamp DESC LIMIT ? OFFSET ?", (limit, offset))


@app.get("/alerts")
def alerts(limit: int = Query(default=30, ge=1, le=200)):
    _ready()
    return warehouse.execute_readonly(
        "SELECT transaction_id, day, region, total_amount, anomaly_type, payment_status "
        "FROM transactions WHERE is_anomaly=1 ORDER BY total_amount DESC LIMIT ?", (limit,))


@app.get("/quality")
def quality():
    path = REPORTS / "data_quality.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Quality report unavailable")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/model-evaluation")
def model_evaluation():
    path = REPORTS / "model_evaluation.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Model report unavailable")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/investigate")
def investigation(body: InvestigationRequest):
    correlation_id = str(uuid4())

    def failure(exc: Exception, status: int, code: str, message: str):
        log_failure(logger, exc, code=code, correlation_id=correlation_id)
        return JSONResponse(status_code=status, headers={"X-Correlation-ID": correlation_id},
                            content={"detail": message, "code": code,
                                     "error_type": type(exc).__name__, "correlation_id": correlation_id})

    try:
        return investigate(body.question, use_langgraph=body.use_langgraph, correlation_id=correlation_id)
    except (ImportError, ModuleNotFoundError) as exc:
        return failure(exc, 400, "investigation_dependency_missing",
                       "Dépendance optionnelle manquante dans le Python de FastAPI. Vérifier les extras agent/rag.")
    except sqlite3.DatabaseError as exc:
        return failure(exc, 503, "warehouse_unavailable", "Entrepôt SQLite indisponible. Consulter les journaux FastAPI.")
    except ValueError as exc:
        return failure(exc, 422, "investigation_configuration_invalid",
                       "Question ou configuration d’investigation invalide. Vérifier RETAILMIND_RETRIEVAL et les paramètres RAG.")
    except TimeoutError as exc:
        return failure(exc, 504, "investigation_timeout",
                       "Délai d’investigation dépassé. Réduire la question ou vérifier les services locaux.")
    except Exception as exc:
        return failure(exc, 500, "investigation_failed",
                       "Erreur interne de l’investigation. Consulter les journaux FastAPI avec la référence indiquée.")


@app.get("/rag/status")
def rag_status():
    return retrieval.index_status()


@app.get("/investigation-status")
def investigation_status():
    return service_status()


@app.get("/rag/documents/{name:path}")
def runbook_document(name: str):
    # Resolve against the corpus allowlist, never open an arbitrary supplied path.
    source = "docs/runbooks/" + name
    for document in retrieval.corpus():
        if document["source"] == source:
            return document
    raise HTTPException(status_code=404, detail="Runbook autorisé introuvable")


@app.post("/predict")
def prediction(body: TransactionFeatures):
    from retailmind.train import predict
    try:
        return predict([body.model_dump()])[0]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# --- Professional React frontend API ----------------------------------------


@app.get("/analytics")
def analytics(period: Literal["7d", "30d", "all"] = "all"):
    """Aggregated values computed from synthetic paid transactions; period relative to latest data row."""
    _ready()
    latest = warehouse.execute_readonly("SELECT MAX(day) AS latest_day FROM transactions")
    max_day = latest[0]["latest_day"] if latest else None
    where = "1=1"
    params: tuple = ()
    if period != "all" and max_day:
        days = 6 if period == "7d" else 29
        where = "day >= date(?, '-' || ? || ' days')"
        params = (max_day, days)
    summary = warehouse.execute_readonly(
        f"SELECT COUNT(*) AS orders, "
        f"ROUND(COALESCE(SUM(CASE WHEN payment_status='paid' THEN total_amount ELSE 0 END),0),2) AS revenue_mad, "
        f"ROUND(COALESCE(SUM(total_amount),0),2) AS gross_value_mad, "
        f"COALESCE(SUM(is_anomaly),0) AS anomalies, "
        f"COALESCE(SUM(CASE WHEN payment_status='failed' THEN 1 ELSE 0 END),0) AS failed_payments "
        f"FROM transactions WHERE {where}", params
    )[0]
    daily = warehouse.execute_readonly(
        f"SELECT day, COUNT(*) AS orders, ROUND(SUM(CASE WHEN payment_status='paid' THEN total_amount ELSE 0 END),2) AS revenue, "
        f"SUM(is_anomaly) AS anomalies FROM transactions WHERE {where} GROUP BY day ORDER BY day", params
    )
    regional = warehouse.execute_readonly(
        f"SELECT region, COUNT(*) AS orders, ROUND(SUM(CASE WHEN payment_status='paid' THEN total_amount ELSE 0 END),2) AS revenue, "
        f"SUM(is_anomaly) AS anomalies FROM transactions WHERE {where} GROUP BY region ORDER BY revenue DESC", params
    )
    categories = warehouse.execute_readonly(
        f"SELECT category, COUNT(*) AS orders, ROUND(SUM(CASE WHEN payment_status='paid' THEN total_amount ELSE 0 END),2) AS revenue "
        f"FROM transactions WHERE {where} GROUP BY category ORDER BY revenue DESC", params
    )
    payments = warehouse.execute_readonly(
        f"SELECT payment_status AS status, COUNT(*) AS orders FROM transactions WHERE {where} "
        f"GROUP BY payment_status ORDER BY orders DESC", params
    )
    types = warehouse.execute_readonly(
        f"SELECT anomaly_type AS type, COUNT(*) AS count FROM transactions WHERE is_anomaly=1 AND {where} "
        f"GROUP BY anomaly_type ORDER BY count DESC", params
    )
    return {"period": period, "latest_day": max_day, "summary": summary, "daily": daily,
            "regions": regional, "categories": categories, "payments": payments, "anomaly_types": types,
            "synthetic": True}


def _page_rows(*, limit: int, offset: int, search: str, region: str,
               status: str, anomaly_only: bool, anomaly_type: str, sort: str):
    conditions: list[str] = []
    params: list = []
    if search.strip():
        conditions.append("(transaction_id LIKE ? OR category LIKE ? OR region LIKE ?)")
        term = f"%{search.strip()[:100]}%"
        params.extend([term, term, term])
    if region:
        conditions.append("region = ?")
        params.append(region)
    if status:
        conditions.append("payment_status = ?")
        params.append(status)
    if anomaly_only:
        conditions.append("is_anomaly = 1")
    if anomaly_type:
        conditions.append("anomaly_type = ?")
        params.append(anomaly_type)
    where = " AND ".join(conditions) or "1=1"
    count = warehouse.execute_readonly(f"SELECT COUNT(*) AS n FROM transactions WHERE {where}", tuple(params))[0]["n"]
    order_sql = {
        "recent": "event_timestamp DESC", "oldest": "event_timestamp ASC",
        "amount_desc": "total_amount DESC", "amount_asc": "total_amount ASC",
    }[sort]
    items = warehouse.execute_readonly(
        f"SELECT transaction_id, day, region, category, channel, quantity, unit_price, discount_pct, "
        f"total_amount, payment_status, is_anomaly, anomaly_type "
        f"FROM transactions WHERE {where} ORDER BY {order_sql} LIMIT ? OFFSET ?",
        tuple(params + [limit, offset]),
    )
    return {"items": items, "total": count, "limit": limit, "offset": offset,
            "has_more": offset + len(items) < count}


@app.get("/transactions-page")
def transactions_page(
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str = Query(default="", max_length=100),
    region: str = Query(default="", max_length=60),
    status: Literal["", "paid", "pending", "failed"] = "",
    anomaly_only: bool = False,
    sort: Literal["recent", "oldest", "amount_desc", "amount_asc"] = "recent",
):
    _ready()
    return _page_rows(limit=limit, offset=offset, search=search, region=region, status=status,
                      anomaly_only=anomaly_only, anomaly_type="", sort=sort)


@app.get("/alerts-page")
def alerts_page(
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str = Query(default="", max_length=100),
    region: str = Query(default="", max_length=60),
    anomaly_type: str = Query(default="", max_length=60),
    sort: Literal["recent", "oldest", "amount_desc", "amount_asc"] = "amount_desc",
):
    _ready()
    return _page_rows(limit=limit, offset=offset, search=search, region=region, status="",
                      anomaly_only=True, anomaly_type=anomaly_type, sort=sort)

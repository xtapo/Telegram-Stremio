from __future__ import annotations

import contextvars
import math
import secrets
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional


_request_id = contextvars.ContextVar("request_id", default="-")
_job_id = contextvars.ContextVar("job_id", default="-")

_lock = threading.RLock()
_counters: Dict[str, int] = defaultdict(int)
_gauges: Dict[str, float] = {}
_latencies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=240))
_flood_waits: deque = deque(maxlen=120)


def new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(5)}"


def request_id() -> str:
    return _request_id.get()


def job_id() -> str:
    return _job_id.get()


@contextmanager
def correlation_context(*, request: Optional[str] = None, job: Optional[str] = None):
    req_token = _request_id.set(request or _request_id.get())
    job_token = _job_id.set(job or _job_id.get())
    try:
        yield
    finally:
        _request_id.reset(req_token)
        _job_id.reset(job_token)


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = float(value)


def increment(name: str, amount: int = 1) -> None:
    with _lock:
        _counters[name] += int(amount)


def observe_latency(name: str, milliseconds: float) -> None:
    with _lock:
        _latencies[name].append(max(0.0, float(milliseconds)))


def record_flood_wait(source: str, seconds: float, client: str = "") -> None:
    seconds = max(0.0, float(seconds or 0))
    now = time.time()
    with _lock:
        _counters["telegram.flood_wait.count"] += 1
        _counters["telegram.flood_wait.seconds"] += int(math.ceil(seconds))
        _flood_waits.append({
            "at": now,
            "source": source,
            "seconds": seconds,
            "client": client,
            "request_id": request_id(),
            "job_id": job_id(),
        })


def _latency_summary(values) -> dict:
    vals = sorted(float(v) for v in values)
    if not vals:
        return {"count": 0, "avg_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    p95_index = min(len(vals) - 1, max(0, math.ceil(len(vals) * 0.95) - 1))
    return {
        "count": len(vals),
        "avg_ms": round(sum(vals) / len(vals), 1),
        "p95_ms": round(vals[p95_index], 1),
        "max_ms": round(vals[-1], 1),
    }


def metrics_snapshot() -> dict:
    cutoff = time.time() - 3600
    with _lock:
        recent_floods = [dict(item) for item in _flood_waits if item["at"] >= cutoff]
        return {
            "counters": dict(_counters),
            "gauges": dict(_gauges),
            "latencies": {name: _latency_summary(values) for name, values in _latencies.items()},
            "flood_wait": {
                "total": int(_counters.get("telegram.flood_wait.count", 0)),
                "seconds_total": int(_counters.get("telegram.flood_wait.seconds", 0)),
                "last_hour": len(recent_floods),
                "recent": recent_floods[-10:][::-1],
            },
        }


async def record_error(
    category: str,
    exc: BaseException | str,
    *,
    operation: str,
    details: Optional[dict] = None,
    severity: str = "error",
    job: Optional[str] = None,
) -> None:
    """Persist operational failures without allowing monitoring to break the workload."""
    increment(f"errors.{category}")
    message = str(exc)
    document = {
        "created_at": datetime.now(timezone.utc),
        "category": str(category),
        "operation": str(operation),
        "severity": str(severity),
        "error_type": type(exc).__name__ if isinstance(exc, BaseException) else "Error",
        "message": message[:2000],
        "request_id": request_id(),
        "job_id": job or job_id(),
        "details": details or {},
    }
    try:
        from Backend import db

        tracking = db.dbs.get("tracking")
        if tracking is not None:
            await tracking["error_history"].insert_one(document)
    except Exception:
        # Monitoring must never mask the original application error.
        return


async def recent_errors(limit: int = 50) -> list[dict]:
    try:
        from Backend import db

        tracking = db.dbs.get("tracking")
        if tracking is None:
            return []
        docs = await tracking["error_history"].find().sort("created_at", -1).limit(max(1, min(limit, 200))).to_list(length=max(1, min(limit, 200)))
        for doc in docs:
            doc["_id"] = str(doc.get("_id", ""))
            created = doc.get("created_at")
            if created is not None and hasattr(created, "isoformat"):
                doc["created_at"] = created.isoformat()
        return docs
    except Exception:
        return []

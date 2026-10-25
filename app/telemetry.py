import json
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger("signet")
logger.setLevel(logging.INFO)


def log_line(trace_id: str, method: str, path: str, status: int, duration_ms: int) -> str:
    return json.dumps(
        {
            "trace_id": trace_id,
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": duration_ms,
            "level": "error" if status >= 400 else "info",
        },
        separators=(",", ":"),
    )


def setup_otel() -> None:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
    resource = Resource.create({"service.name": "signet"})
    tracer_provider = TracerProvider(resource=resource)
    if endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
        )
    trace.set_tracer_provider(tracer_provider)
    if not endpoint:
        return
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
        export_interval_millis=5000,
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    global _request_duration
    _request_duration = metrics.get_meter("signet").create_histogram(
        "http.server.request.duration",
        unit="s",
        description="Duration of HTTP requests served by Signet.",
    )
    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{endpoint}/v1/logs"))
    )
    logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=log_provider))


_samples: deque = deque(maxlen=5000)
_sample_lock = threading.Lock()
BOARD_WINDOW_SEC = 900
BOARD_BUCKET_SEC = 30


_NOISE_EXACT = {
    "/favicon.ico",
    "/robots.txt",
    "/apple-touch-icon.png",
    "/apple-touch-icon-precomposed.png",
    "/manifest.json",
    "/browserconfig.xml",
}
_NOISE_SUFFIXES = (".ico", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".woff", ".woff2", ".map")


def noise_path(path: str) -> bool:
    clean = path.split("?", 1)[0].lower()
    if clean in _NOISE_EXACT or clean == "/ops/board":
        return True
    return clean.endswith(_NOISE_SUFFIXES)


def remember_request(method: str, path: str, status: int, duration_ms: int, trace_id: str) -> None:
    if noise_path(path):
        return
    row = {
        "t": time.time(),
        "method": method[:16],
        "path": path[:180],
        "status": int(status),
        "duration_ms": int(duration_ms),
        "trace_id": trace_id,
    }
    with _sample_lock:
        _samples.append(row)


def _percentile(values: list[int], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * q
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def board_snapshot() -> dict:
    now = time.time()
    start = now - BOARD_WINDOW_SEC
    with _sample_lock:
        rows = [row for row in _samples if row["t"] >= start and not noise_path(row["path"])]
    buckets = []
    count = BOARD_WINDOW_SEC // BOARD_BUCKET_SEC
    for index in range(count):
        left = start + index * BOARD_BUCKET_SEC
        right = left + BOARD_BUCKET_SEC
        chunk = [row for row in rows if left <= row["t"] < right]
        rates: dict[str, float] = {}
        for row in chunk:
            key = str(row["status"])
            rates[key] = rates.get(key, 0) + 1
        for key in list(rates):
            rates[key] = round(rates[key] / BOARD_BUCKET_SEC, 4)
        durations = [row["duration_ms"] for row in chunk]
        buckets.append(
            {
                "t": int(left),
                "rates": rates,
                "p95": round(_percentile(durations, 0.95), 1) if durations else None,
                "p99": round(_percentile(durations, 0.99), 1) if durations else None,
            }
        )
    errors = sum(1 for row in rows if row["status"] >= 400)
    avg = round(sum(row["duration_ms"] for row in rows) / len(rows), 1) if rows else None
    logs = []
    for row in reversed(rows[-80:]):
        logs.append(
            {
                "timestamp": datetime.fromtimestamp(row["t"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "method": row["method"],
                "path": row["path"],
                "status": row["status"],
                "duration_ms": row["duration_ms"],
                "trace_id": row["trace_id"],
                "level": "error" if row["status"] >= 400 else "info",
            }
        )
    return {
        "window_sec": BOARD_WINDOW_SEC,
        "bucket_sec": BOARD_BUCKET_SEC,
        "stats": {
            "requests": len(rows),
            "error_rate": round(errors / len(rows), 4) if rows else 0,
            "avg_ms": avg,
        },
        "buckets": buckets,
        "logs": logs,
    }


_request_duration = None


def count_request(method: str, path: str, status: int, duration_ms: int | None = None) -> None:
    meter = metrics.get_meter("signet")
    counter = meter.create_counter("signet_requests_total")
    counter.add(1, {"method": method, "path": path, "status": str(status)})
    if _request_duration is not None and duration_ms is not None:
        _request_duration.record(
            max(duration_ms, 0) / 1000,
            {"method": method, "path": path, "status": str(status)},
        )

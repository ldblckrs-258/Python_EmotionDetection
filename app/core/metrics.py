# Prometheus metrics for FastAPI
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.responses import Response as StarletteResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('http_request_latency_seconds', 'HTTP request latency', ['endpoint'])
FACE_DETECTION_ACCURACY = Gauge('face_detection_accuracy', 'Face detection accuracy (percentage)')

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        endpoint = request.url.path
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(process_time)
        REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, http_status=response.status_code).inc()
        return response

def metrics_endpoint():
    return StarletteResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

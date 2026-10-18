import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from src.logging import logger

class LatencyMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        response: Response = await call_next(request)
        
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        
        logger.info(
            f"HTTP {request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)"
        )
        return response

import pybreaker, multiprocessing

from fastapi import Request, status
from fastapi.responses import JSONResponse
from ..default import ErrorMessages
from .errors import AppException
from slowapi.errors import RateLimitExceeded


async def circuit_breaker_exception_handler(
  request: Request, exc: pybreaker.CircuitBreakerError
):
  return ErrorMessages.CIRCUIT_BREAKER.to_response(status.HTTP_503_SERVICE_UNAVAILABLE)


async def multi_timeout_exception_handler(
  request: Request, exc: multiprocessing.TimeoutError
):
  return ErrorMessages.TIMEOUT.to_response(status.HTTP_504_GATEWAY_TIMEOUT)


async def global_exception_handler(request: Request, exc: Exception):
  return ErrorMessages.SERVER.to_response(status.HTTP_500_INTERNAL_SERVER_ERROR)


async def app_exception_handler(request: Request, exc: AppException):
  return exc.error_enum.to_response(exc.status_code)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
  detail = getattr(exc, "detail", str(exc))
  retry_after = getattr(exc, "reset_after", "60")
  return JSONResponse(
    {"error": f"Rate limit exceeded: {detail}"},
    status_code=429,
    headers={"Retry-After": str(retry_after)},
  )


def register_exception_handlers(app):
  app.add_exception_handler(
    pybreaker.CircuitBreakerError, circuit_breaker_exception_handler
  )
  app.add_exception_handler(
    multiprocessing.TimeoutError, multi_timeout_exception_handler
  )
  app.add_exception_handler(Exception, global_exception_handler)
  app.add_exception_handler(AppException, app_exception_handler)
  app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

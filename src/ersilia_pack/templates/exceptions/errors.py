import pybreaker, time
from fastapi import HTTPException
from pybreaker import CircuitMemoryStorage
from ..default import ErrorMessages, FAIL_MAX, RESET_TIMEOUT


class AppException(Exception):
  def __init__(self, status_code: int, error_enum: ErrorMessages):
    self.status_code = status_code
    self.error_enum = error_enum


class ProcessingCircuitBreaker(pybreaker.CircuitBreaker):
  def __init__(self):
    super().__init__(
      fail_max=FAIL_MAX,
      reset_timeout=RESET_TIMEOUT,
      exclude=[HTTPException(status_code=400)],
      state_storage=CircuitMemoryStorage(pybreaker.STATE_CLOSED),
    )
    self.last_failure_time = None

  def _is_server_error(self, exc):
    return isinstance(exc, HTTPException) and exc.status_code >= 500

  @property
  def next_reset(self):
    if self.current_state == pybreaker.STATE_OPEN and self.last_failure_time:
      return self.last_failure_time + self.reset_timeout
    return None

  def on_failure(self, exc):
    self.last_failure_time = time.time()
    super().on_failure(exc)


class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
  def state_change(self, cb, old_state, new_state):
    print(f"Circuit state changed from {old_state} to {new_state}")
    if new_state == pybreaker.STATE_OPEN:
      cb.next_reset = time.time() + cb.reset_timeout
    elif new_state == pybreaker.STATE_CLOSED:
      cb.next_reset = None


breaker = ProcessingCircuitBreaker()
breaker.add_listener(CircuitBreakerListener())

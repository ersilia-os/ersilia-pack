import psutil
from fastapi import APIRouter

from ..exceptions.errors import breaker


router = APIRouter()


@router.get("/healthz", tags=["Monitoring"])
def health_check():
  status = {
    "breaker": {
      "state": breaker.current_state,
      "failures": breaker.fail_counter,
      "last_failure": breaker.last_failure_time,
      "reset_timeout": breaker.reset_timeout,
      "next_reset": breaker.next_reset,
    },
    "system": {"cpu": psutil.cpu_percent(), "memory": psutil.virtual_memory().percent},
  }
  return status

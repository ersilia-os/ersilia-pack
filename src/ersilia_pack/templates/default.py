import os, tempfile, traceback, uuid
from datetime import datetime
from fastapi.responses import JSONResponse
from typing import List
from enum import Enum
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_VERSION = os.environ.get("MODEL_VERSION", "1.0")
RUNTIME = os.environ.get("RUNTIME", "python")
MIN_WORKERS = int(os.environ.get("MIN_WORKERS", 1))
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 1))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", 10000))
MAX_BATCH_DELAY = int(os.environ.get("MAX_BATCH_DELAY", 5000))
LOADED_AT_STARTUP = os.environ.get("LOADED_AT_STARTUP", "False").lower() in (
  "true",
  "1",
  "yes",
)


REDOC_JS_URL = "https://unpkg.com/redoc@next/bundles/redoc.standalone.js"
MATE_CSS_URL = "https://cdn.jsdelivr.net/gh/ajatkj/swagger-ui-improved-theme/css/swagger-ui-improved.css"
API_DESCIPTION = """
Ersilia Pack is an open-source model serving framework built for researchers and scientists, offering endpoints for seamless model deployment and monitoring. It provides `/metrics` for Prometheus-based performance insights, `/metadata`\n for detailed model information, and `/info` to quickly retrieve the prediction endpoint name. The core `/run` endpoint offers sub-routes for example inputs/outputs, input/output column details, and a POST method that handles\n predictions with dynamic resource planning and multiprocessing. Additionally, the `/health` endpoint delivers system status and circuit breaker information—which trips after five consecutive failures with a 30-second reset—while enforcing a rate-\nlimit of 100 requests per minute.
"""
FRAMEWORK_FOLDER = os.path.abspath(os.path.join(ROOT, "..", "model", "framework"))
MODEL_ROOT = os.path.abspath(os.path.join(ROOT, "..", "model"))
TEMP_FOLDER = tempfile.mkdtemp(prefix="ersilia-")
BUNDLE_FOLDER = os.path.abspath(os.path.join(ROOT, ".."))
generic_example_output_file = "output.csv"
generic_example_input_file = "input.csv"

ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
DEFAULT_REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_EXPIRATION = int(
  os.getenv("REDIS_EXPIRATION", 3600 * 24 * 7)
)  # One week just as default expiration
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", 2))
MAX_WAIT_TIME = os.getenv("MAX_WAIT_TIME", 0.1)
FAIL_MAX = os.getenv("FAIL_MAX", 6)
RESET_TIMEOUT = os.getenv("RESET_TIMEOUT", 60)
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")
RATE_LIMIT_LOCAL = os.getenv("RATE_LIMIT", "10000000/minute")
DEFAULT_TIMEOUT = os.getenv("TIMEOUT", 60)  # TODO: More accurate timeout
MAX_CPU_PERC = float(os.getenv("MAX_CPU_PERC", 90.0))
MAX_MEM_PERC = float(os.getenv("MAX_MEM_PERC", 90.0))
DATA_SIZE_UPPERBOUND = os.getenv("DATA_SIZE_UPPERBOUND", 10_000)
DATA_SIZE_LOWERBOUND = os.getenv("DATA_SIZE_LOWERBOUND", 1000)
RESOURCE_SAFETY_MARGIN = os.getenv("RESOURCE_SAFETY_MARGIN", 0.8)
MODEL_THRESHOLD_FRACTION = float(os.getenv("MODEL_THRESHOLD_FRACTION", 0.13))
HISTOGRAM_TIME_INTERVAL = os.getenv(
  "HISTOGRAM_TIME_INTERVAL", (0.1, 0.3, 0.5, 1.0, 2.0, 3.0, 4.0)
)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*").strip()
if allowed_origins_env == "*":
  ALLOWED_ORIGINS = ["*"]
else:
  ALLOWED_ORIGINS = [
    origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()
  ]

OUTPUT_CONSISTENCY = "Output Consistency"


class OrientEnum(str, Enum):
  RECORDS = "records"
  COLUMNS = "columns"
  VALUES = "values"
  SPLIT = "split"
  INDEX = "index"


class CardField(str, Enum):
  identifier = "Identifier"
  slug = "Slug"
  description = "Description"
  input = "Input"


API_ID = str(uuid.uuid4())
API_START_TIME = datetime.utcnow().isoformat() + "Z"
ROOT_ENDPOINT_LOADED = False


class Worker(BaseModel):
  id: str
  startTime: str
  status: str
  memoryUsage: float
  pid: int


class APIInfo(BaseModel):
  modelName: str
  modelVersion: str
  runtime: str
  minWorkers: int
  maxWorkers: int
  maxBatchSize: int
  maxBatchDelay: int
  loadedAtStartup: bool
  workers: List[Worker]


class ErrorMessages(str, Enum):
  CIRCUIT_BREAKER = "Service temporarily unavailable due to high error rate and exited by circuit breaker"
  SERVER = "Internal processing error due to a shell execution"
  TIMEOUT = f"Processing timed out after {DEFAULT_TIMEOUT} seconds"
  INCONSISTENT_HEADER = "Inconsistent output headers across workers"
  RESOURCE = "System resources over threshold"
  EMPTY_DATA = "Data is empty."
  EMPTY_REQUEST = "API request is empty."
  RATE_LIMIT_EXCEEDED = "Rate limit exceeded for the request."

  def to_response(self, status_code: int) -> JSONResponse:
    content = {"detail": self.value}
    if ENVIRONMENT != "prod":
      content["traceback"] = traceback.format_exc()
    return JSONResponse(status_code=status_code, content=content)

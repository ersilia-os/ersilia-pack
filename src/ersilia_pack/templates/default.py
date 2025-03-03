import os, tempfile, traceback
from fastapi.responses import JSONResponse
from enum import Enum

ROOT = os.path.dirname(os.path.abspath(__file__))


def get_api_names_from_sh(framework_dir):
  if not os.path.exists(framework_dir):
    return

  api_names = []
  for l in os.listdir(framework_dir):
    if l.endswith(".sh"):
      api_names += [l.split(".sh")[0]]
  if len(api_names) == 0:
    raise Exception("No API names found. An API should be a .sh file")
  return api_names


REDOC_JS_URL = "https://unpkg.com/redoc@next/bundles/redoc.standalone.js"
MATE_CSS_URL = "https://cdn.jsdelivr.net/gh/ajatkj/swagger-ui-improved-theme/css/swagger-ui-improved.css"
API_DESCIPTION = """
Ersilia Pack is an open-source model serving framework built for researchers and scientists, offering endpoints for seamless model deployment and monitoring. It provides `/metrics` for Prometheus-based performance insights, `/metadata`\n for detailed model information, and `/info` to quickly retrieve the prediction endpoint name. The core `/run` endpoint offers sub-routes for example inputs/outputs, input/output column details, and a POST method that handles\n predictions with dynamic resource planning and multiprocessing. Additionally, the `/health` endpoint delivers system status and circuit breaker information—which trips after five consecutive failures with a 30-second reset—while enforcing a rate-\nlimit of 100 requests per minute.
"""
FRAMEWORK_FOLDER = os.path.abspath(os.path.join(ROOT, "..", "model", "framework"))
MODEL_ROOT = os.path.abspath(os.path.join(ROOT, "..", "model"))
TEMP_FOLDER = tempfile.mkdtemp(prefix="ersilia-")
BUNDLE_FOLDER = os.path.abspath(os.path.join(ROOT, ".."))
API_NAMES = get_api_names_from_sh(FRAMEWORK_FOLDER)
api_name = API_NAMES[0] if isinstance(API_NAMES, list) else API_NAMES
api_input_path = os.path.join(FRAMEWORK_FOLDER, "examples", f"{api_name}_input.csv")
generic_input_path = os.path.join(FRAMEWORK_FOLDER, "examples", "input.csv")

api_output_path = os.path.join(FRAMEWORK_FOLDER, "examples", f"{api_name}_output.csv")
generic_output_path = os.path.join(FRAMEWORK_FOLDER, "examples", "output.csv")

if os.path.exists(api_input_path):
    EXAMPLE_INPUT_PATH = api_input_path
else:
    EXAMPLE_INPUT_PATH = generic_input_path

if os.path.exists(api_output_path):
    EXAMPLE_OUTPUT_PATH = api_output_path
else:
    EXAMPLE_OUTPUT_PATH = generic_output_path

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

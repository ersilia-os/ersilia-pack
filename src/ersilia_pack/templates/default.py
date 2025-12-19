import logging, os, tempfile, traceback, sys, uuid
from datetime import datetime
from fastapi.responses import JSONResponse
from typing import List
from pathlib import Path
from enum import Enum
from pydantic import BaseModel

# ruff: noqa: E501
ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_VERSION = os.environ.get("MODEL_VERSION", "1.0")
EOS_TMP = os.path.join(os.path.join(str(Path.home()), "eos"), "temp")
EOS_TMP_TASKS = os.path.join(EOS_TMP, "tasks")
if not os.path.exists(EOS_TMP_TASKS):
  os.makedirs(EOS_TMP_TASKS, exist_ok=True)
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
This server provides `/metrics` for Prometheus-based performance insights, `/metadata` for detailed model information, and `/info` to quickly retrieve the prediction endpoint name. The core `/run` endpoint offers sub-routes\n for example inputs/outputs, input/output column details, and a POST method that handles predictions with dynamic resource planning and multiprocessing. Additionally, the `/health` endpoint delivers system status and circuit breaker information\n which trips after five consecutive failures with a 30-second reset—while enforcing a rate-limit of 100 requests per minute.
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
FAIL_MAX = int(os.getenv("FAIL_MAX", 100))
RESET_TIMEOUT = os.getenv("RESET_TIMEOUT", 60)
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")
RATE_LIMIT_LOCAL = os.getenv("RATE_LIMIT", "10000000/minute")
DEFAULT_TIMEOUT = os.getenv("TIMEOUT", 60)  # TODO: More accurate timeout
MAX_CPU_PERC = float(os.getenv("MAX_CPU_PERC", 90.0))
MAX_MEM_PERC = float(os.getenv("MAX_MEM_PERC", 90.0))
DATA_SIZE_UPPERBOUND = os.getenv("DATA_SIZE_UPPERBOUND", 10_000)
DATA_SIZE_LOWERBOUND = os.getenv("DATA_SIZE_LOWERBOUND", 100)
RESOURCE_SAFETY_MARGIN = os.getenv("RESOURCE_SAFETY_MARGIN", 0.8)
MODEL_THRESHOLD_FRACTION = float(os.getenv("MODEL_THRESHOLD_FRACTION", 0.13))
HISTOGRAM_TIME_INTERVAL = os.getenv(
  "HISTOGRAM_TIME_INTERVAL", (0.1, 0.3, 0.5, 1.0, 2.0, 3.0, 4.0)
)
MEDIA_TYPE = "application/octet-stream"
CONTENT_DESP = "attachment; filename=result.bin"
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


class TaskTypeEnum(str, Enum):
  HEAVY = "heavy"
  SIMPLE = "simple"


class CardField(str, Enum):
  identifier = "Identifier"
  slug = "Slug"
  title = "Title"
  description = "Description"
  input = "Input"
  task = "Task"
  subtask = "Subtask"


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


class Ansi:
  RESET = "\033[0m"
  BOLD = "\033[1m"
  DIM = "\033[2m"
  UNDERLINE = "\033[4m"
  REVERSE = "\033[7m"
  FG = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "bright_black": 90,
    "bright_red": 91,
    "bright_green": 92,
    "bright_yellow": 93,
    "bright_blue": 94,
    "bright_magenta": 95,
    "bright_cyan": 96,
    "bright_white": 97,
  }
  BG = {
    "on_black": 40,
    "on_red": 41,
    "on_green": 42,
    "on_yellow": 43,
    "on_blue": 44,
    "on_magenta": 45,
    "on_cyan": 46,
    "on_white": 47,
    "on_bright_black": 100,
    "on_bright_red": 101,
    "on_bright_green": 102,
    "on_bright_yellow": 103,
    "on_bright_blue": 104,
    "on_bright_magenta": 105,
    "on_bright_cyan": 106,
    "on_bright_white": 107,
  }

  @staticmethod
  def code(*, fg=None, bg=None, bold=False, dim=False, underline=False, reverse=False):
    """
    Build the ANSI escape sequence for the given styles.
    fg, bg: keys in Ansi.FG / Ansi.BG
    bold, dim, underline, reverse: booleans
    """
    parts = []
    if bold:
      parts.append("1")
    if dim:
      parts.append("2")
    if underline:
      parts.append("4")
    if reverse:
      parts.append("7")
    if fg:
      code = Ansi.FG.get(fg.lower())
      if code is None:
        raise ValueError(f"Unknown fg color: {fg}")
      parts.append(str(code))
    if bg:
      code = Ansi.BG.get(bg.lower())
      if code is None:
        raise ValueError(f"Unknown bg color: {bg}")
      parts.append(str(code))
    if not parts:
      return ""
    return f"\033[{';'.join(parts)}m"

  @staticmethod
  def color(
    text, *, fg=None, bg=None, bold=False, dim=False, underline=False, reverse=False
  ):
    start = Ansi.code(
      fg=fg, bg=bg, bold=bold, dim=dim, underline=underline, reverse=reverse
    )
    end = Ansi.RESET if start else ""
    return f"{start}{text}{end}"


def colored(
  text, fg=None, bg=None, bold=False, dim=False, underline=False, reverse=False
):
  return Ansi.color(
    text, fg=fg, bg=bg, bold=bold, dim=dim, underline=underline, reverse=reverse
  )


def cprint(text, **kwargs):
  print(colored(text, **kwargs))


RESET = "\033[0m"
COLORS = {
  logging.DEBUG: "\033[90m",
  logging.INFO: "\033[36m",
  logging.WARNING: "\033[33m",
  logging.ERROR: "\033[31m",
  logging.CRITICAL: "\033[1;31m",
}


class ColorFormatter(logging.Formatter):
  def format(self, record):
    color = COLORS.get(record.levelno, "")
    fmt = f"{color}%(message)s{RESET}"
    formatter = logging.Formatter(fmt)
    return formatter.format(record)


def get_logger(name=None, level=logging.INFO):
  logger = logging.getLogger(name if name is not None else __name__)

  if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())
    logger.addHandler(handler)

  logger.setLevel(level)
  logger.propagate = False
  return logger


logger = get_logger()

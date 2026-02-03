import datetime, logging, os, socket, subprocess, shlex, shutil, sys
from collections import namedtuple
from pathlib import Path

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


def find_free_port(host="localhost"):
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.bind((host, 0))
  port = s.getsockname()[1]
  s.close()
  return int(port)


def run_command(cmd, quiet=None):
  shell = isinstance(cmd, str)
  if shell:
    run_cmd = cmd
    display_cmd = cmd
  else:
    run_cmd = [os.fspath(c) for c in cmd]
    display_cmd = " ".join(shlex.quote(x) for x in run_cmd)

  start = datetime.datetime.now()

  proc = subprocess.Popen(
    run_cmd,
    shell=shell,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    universal_newlines=True,
  )

  stdout_lines = []
  stderr_lines = []

  logger.info(f"$ {display_cmd}")

  for line in proc.stdout:
    line = line.rstrip("\n")
    stdout_lines.append(line)
    if not quiet:
      logger.info(line)

  for line in proc.stderr:
    line = line.rstrip("\n")
    stderr_lines.append(line)
    if not quiet:
      logger.error(line)

  proc.wait()
  end = datetime.datetime.now()

  stdout_str = "\n".join(stdout_lines)
  stderr_str = "\n".join(stderr_lines)

  CommandResult = namedtuple("CommandResult", ["returncode", "stdout", "stderr"])
  output = CommandResult(
    returncode=proc.returncode,
    stdout=stdout_str,
    stderr=stderr_str,
  )

  logger.info(f"returncode: {proc.returncode}")
  logger.info(f"duration: {(end - start).total_seconds():.3f}s")
  logger.info("-" * 40)

  return output


def eval_conda_prefix() -> str:
  conda_exe = os.environ.get("CONDA_EXE") or shutil.which("conda")

  if not conda_exe:
    env_prefix = os.environ.get("CONDA_PREFIX")
    if env_prefix:
      base_candidate = Path(env_prefix).parents[1]
      candidate = base_candidate / "bin" / "conda"
      if candidate.exists():
        conda_exe = str(candidate)

  if not conda_exe:
    return ""

  p = subprocess.run([conda_exe, "info", "--base"], capture_output=True, text=True)
  if p.returncode != 0:
    return ""
  return p.stdout.strip()

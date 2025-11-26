import datetime, logging, os, socket, subprocess, shlex
from collections import namedtuple


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

  print(f"[{start.strftime('%Y-%m-%d %H:%M:%S')}] $ {display_cmd}")

  for line in proc.stdout:
    line = line.rstrip("\n")
    stdout_lines.append(line)
    print(line)
    if not quiet:
      logger.info(line)

  for line in proc.stderr:
    line = line.rstrip("\n")
    stderr_lines.append(line)
    print(line)
    if not quiet:
      logger.info(line)

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

  print(
    "\n".join([
      f"returncode: {proc.returncode}",
      f"duration: {(end - start).total_seconds():.3f}s",
      "-" * 40,
    ])
  )

  return output


def get_logger():
  logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  )
  logger = logging.getLogger(__name__)
  return logger


def eval_conda_prefix():
  # This returns an empty string if conda is not discoverable
  return os.popen("conda info --base").read().strip()


logger = get_logger()

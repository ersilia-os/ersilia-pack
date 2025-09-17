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
  result = subprocess.run(
    run_cmd,
    shell=shell,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=os.environ,
  )
  end = datetime.datetime.now()

  CommandResult = namedtuple("CommandResult", ["returncode", "stdout", "stderr"])
  stdout_str = result.stdout.strip()
  stderr_str = result.stderr.strip()
  output = CommandResult(
    returncode=result.returncode, stdout=stdout_str, stderr=stderr_str
  )

  log_lines = [
    f"[{start.strftime('%Y-%m-%d %H:%M:%S')}] $ {display_cmd}",
  ]
  if stdout_str:
    log_lines += ["stdout:", stdout_str]
  if stderr_str:
    log_lines += ["stderr:", stderr_str]
  log_lines += [
    f"returncode: {result.returncode}",
    f"duration: {(end - start).total_seconds():.3f}s",
    "-" * 40,
  ]
  print("\n".join(log_lines))

  if not quiet:
    if stdout_str:
      logger.error(stdout_str)
    if stderr_str:
      logger.error(stderr_str)

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

import ast, json, os, re, subprocess, sys, threading

from .default import FRAMEWORK_FOLDER, ROOT, cprint

# Warm serving keeps a model loaded between batches in a long-lived worker
# process. A model opts in by giving main.py a load_tool() and a run_tool(model, in, out)
# function. Every other model keeps the cold path: run.sh once per batch.

WARM_ENV_VAR = "ERSILIA_WARM"
WORKER_SCRIPT = os.path.join(ROOT, "warm_worker.py")
MAIN_PY = os.path.join(FRAMEWORK_FOLDER, "code", "main.py")
RUN_SH = os.path.join(FRAMEWORK_FOLDER, "run.sh")

# The only run.sh shape the worker can stand in for: one line calling main.py.
_RUN_SH_LINE = re.compile(r"^(\S+)\s+\$1/code/main\.py\s+\$2\s+\$3$")


def _log(text, **kwargs):
  # stdout is redirected to the serve log; flush so each line shows up as it
  # happens. The [warm] prefix makes the path a model takes easy to grep.
  cprint(f"[warm] {text}", **kwargs)
  sys.stdout.flush()


class WarmWorkerDied(Exception):
  pass


class WarmRunError(Exception):
  pass


def _run_sh_python():
  if not os.path.exists(RUN_SH):
    return None
  with open(RUN_SH, "r") as f:
    lines = [l.strip() for l in f]
  lines = [l for l in lines if l and not l.startswith("#")]
  if len(lines) != 1:
    return None
  match = _RUN_SH_LINE.match(lines[0])
  return match.group(1) if match else None


def _main_py_is_warm():
  if not os.path.exists(MAIN_PY):
    return False
  with open(MAIN_PY, "r") as f:
    try:
      tree = ast.parse(f.read())
    except SyntaxError:
      return False
  names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
  return {"load_tool", "run_tool"} <= names


def detect_python():
  # Returns the interpreter to start the worker with, or None for the cold path.
  if os.environ.get(WARM_ENV_VAR, "1").lower() in ("0", "false", "no"):
    return None
  python_exe = _run_sh_python()
  if python_exe is None or not _main_py_is_warm():
    return None
  return python_exe


class WarmWorker(object):
  def __init__(self, python_exe):
    self.python_exe = python_exe
    self.lock = threading.Lock()
    self.proc = None
    self.loaded = False
    # Set when load_tool() fails: the model then stays on the cold path for good.
    self.disabled = False

  def _start(self):
    _log(f"Starting worker with {self.python_exe}", fg="blue")
    self.proc = subprocess.Popen(
      [self.python_exe, WORKER_SCRIPT, MAIN_PY],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      text=True,
      bufsize=1,
    )
    message = self._read()
    if message is None or message.get("status") != "ready":
      error = message.get("error") if message else "worker exited during load"
      _log(f"Worker failed to load the model, using run.sh from now on:\n{error}", fg="red")
      self.disabled = True
      self._stop()
      return
    self.loaded = True
    _log("Model loaded in worker: new structure (load_tool + run_tool)", fg="green", bold=True)

  def _read(self):
    line = self.proc.stdout.readline()
    return json.loads(line) if line else None

  def _stop(self):
    self.loaded = False
    if self.proc is None:
      return
    if self.proc.poll() is None:
      self.proc.stdin.close()
      try:
        self.proc.wait(timeout=10)
      except subprocess.TimeoutExpired:
        self.proc.kill()
    self.proc = None

  def _alive(self):
    return self.proc is not None and self.proc.poll() is None

  def ensure_loaded(self):
    with self.lock:
      if not self.disabled and not self._alive():
        self._start()
      return not self.disabled

  def run(self, input_file, output_file):
    # Raises WarmWorkerDied if the worker cannot be used (the caller should
    # fall back to run.sh) and WarmRunError if the model's run_tool() failed.
    with self.lock:
      if self.disabled:
        raise WarmWorkerDied("warm worker is disabled")
      if not self._alive():
        self._start()
        if self.disabled:
          raise WarmWorkerDied("warm worker could not load the model")
      try:
        self.proc.stdin.write(json.dumps({"input": input_file, "output": output_file}))
        self.proc.stdin.write("\n")
        self.proc.stdin.flush()
        message = self._read()
      except (BrokenPipeError, ValueError):
        message = None
      if message is None:
        # The next call starts a fresh worker.
        self._stop()
        raise WarmWorkerDied("warm worker exited while running a batch")
      if not message.get("ok"):
        raise WarmRunError(message.get("error"))

  def close(self):
    with self.lock:
      self._stop()


_worker = None


def get_worker():
  return _worker


def is_active():
  return _worker is not None and not _worker.disabled


def is_loaded():
  return is_active() and _worker.loaded


def start():
  # Called at app startup. Loading runs in a thread so the server comes up
  # straight away; requests wait on the worker lock until the model is ready.
  global _worker
  python_exe = detect_python()
  if python_exe is None:
    _log("Not available for this model: old structure (run.sh per batch)", fg="blue")
    return
  _worker = WarmWorker(python_exe)
  threading.Thread(target=_worker.ensure_loaded, daemon=True).start()


def stop():
  if _worker is not None:
    _worker.close()


def run_framework(input_file, output_file):
  # Runs one chunk through the warm worker when possible, else through run.sh.
  if is_active():
    try:
      _worker.run(input_file, output_file)
      _log("Batch run in the loaded model (worker)", fg="green")
      return
    except WarmWorkerDied as e:
      _log(f"{e}. Running this batch with run.sh", fg="yellow")
    except WarmRunError as e:
      raise RuntimeError(f"Model run failed in warm worker:\n{e}")
  _log("Batch run with run.sh", fg="blue")
  cmd = f"bash {FRAMEWORK_FOLDER}/run.sh {FRAMEWORK_FOLDER} {input_file} {output_file} {ROOT}"
  subprocess.run(cmd, shell=True, check=True)

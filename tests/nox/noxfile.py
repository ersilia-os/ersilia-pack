import json, nox, os, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import match, tools, shim_bash, srv_bg, srv_kill, run, http, ready, read_values

ROOT = Path.home() / "eos"
PLAY = ROOT / "erp_playground"
PLAY.mkdir(parents=True, exist_ok=True)
PWD = Path(__file__).resolve().parent.parent.parent
nox.options.envdir = str(PLAY / ".nox")

@nox.session(
  venv_backend="conda", python=["3.8" ,"3.9", "3.10", "3.11", "3.12"], reuse_venv=True
)
def ci(s):
  model = s.posargs[0] if len(s.posargs) >= 1 else "eos3b5e"
  port = int(s.posargs[1]) if len(s.posargs) >= 2 else 8000
  payload = Path(s.posargs[2]) if len(s.posargs) >= 3 else Path("data/payload.json")
  envname = s.posargs[3] if len(s.posargs) >= 4 else model
  model_path = PLAY / model

  log = Path(f"{model_path}-serve.log")
  pidf = Path(f"{model_path}.pid")
  repo = ROOT / "repository"
  bundle = repo / model
  base = f"http://127.0.0.1:{port}"

  tools(s)

  b = Path(sys.executable).parent
  s.env["PATH"] = str(b) + os.pathsep + s.env.get("PATH", "")
  s.env["PYTHON"] = sys.executable
  s.env["CONDA_PREFIX"] = str(Path(sys.prefix))
  shim_bash(s)

  if Path(model_path).exists():
    shutil.rmtree(model_path)
  if bundle.exists():
    shutil.rmtree(bundle, ignore_errors=True)
  if pidf.exists():
    pidf.unlink()
  if log.exists():
    log.unlink()

  run(s, "git", "clone", "--depth", "1", f"https://github.com/ersilia-os/{model}.git", model_path)
  run(s, "ersilia_model_lint", "--repo_path", model_path)
  repo.mkdir(parents=True, exist_ok=True)
  run(
    s,
    "ersilia_model_pack",
    "--repo_path",
    model_path,
    "--bundles_repo_path",
    str(repo),
    "--conda_env_name",
    envname,
  )

  exe = b / "ersilia_model_serve"
  if not exe.exists():
    s.error(f"serve not found: {exe}")

  log.touch()
  pid = srv_bg(s, exe, bundle, port, log, pidf)

  ep = ready(base, 45)
  if not ep:
    txt = log.read_text() if log.exists() else ""
    srv_kill(s, pid)
    s.error(f"server not healthy\n{txt}")
  else:
    print(f"ready via {ep}")

  if not payload.exists():
    srv_kill(s, pid)
    s.error(f"payload not found: {payload}")
  input_path = Path(model_path) / "model" / "framework" / "examples" / "run_input.csv"

  data = read_values(input_path)
  data = [d[0] for d in data]
  body = http(f"{base}/run", data)
  try:
    output_path = Path(model_path) / "model" / "framework" / "examples" / "run_output.csv"
    exp_res = json.loads(body)
    exp_res = [list(e.values()) for e in exp_res]
    exp_res = [float(v) for vs in exp_res for v in vs]
    act_res = read_values(output_path)
    act_res = [float(v) for vs in act_res for v in vs]
    if not match(act_res, exp_res):
      raise RuntimeError("Result did not match")
    
  except Exception as e:
    s.error(e)
    txt = log.read_text() if log.exists() else ""
    srv_kill(s, pid)
    s.error(f"/run non-json\n{body}\n{txt}")

  interval = int(os.environ.get("JOB_POLL_INTERVAL", "2"))
  timeout = int(os.environ.get("JOB_POLL_TIMEOUT", "120"))

  sub = http(f"{base}/job/submit", json.loads(payload.read_text()))
  try:
    jid = json.loads(sub).get("job_id")
  except Exception:
    srv_kill(s, pid)
    s.error(f"/job/submit non-json\n{sub}")
  if not jid or jid == "null":
    srv_kill(s, pid)
    s.error(f"invalid job_id\n{sub}")

  t0 = time.time()
  status = None
  while time.time() - t0 < timeout:
    try:
      st = json.loads(http(f"{base}/job/status/{jid}"))
      status = st.get("status")
      print(f"[{int(time.time() - t0)}s] status = {status}")
      if status == "completed":
        break
      if status == "failed":
        txt = log.read_text() if log.exists() else ""
        srv_kill(s, pid)
        s.error(f"job failed\n{json.dumps(st)}\n{txt}")
    except Exception as e:
      txt = log.read_text() if log.exists() else ""
      srv_kill(s, pid)
      s.error(f"/job/status error: {e}\n{txt}")
    time.sleep(interval)

  if status != "completed":
    txt = log.read_text() if log.exists() else ""
    srv_kill(s, pid)
    s.error(f"timeout {timeout}s\n{txt}")

  res = http(f"{base}/job/result/{jid}")
  try:
    s.log("Job endpoints are in a correct behaviour!")
  except Exception as e:
    srv_kill(s, pid)
    s.error(f"/job/result non-json\n{res}. {e}")

  srv_kill(s, pid)

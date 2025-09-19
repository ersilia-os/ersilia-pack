import csv, json, math, nox, os, sys, time, urllib.request
from pathlib import Path

ROOT = Path.home() / "eos"
PLAY = ROOT / "erp_playground"
PLAY.mkdir(parents=True, exist_ok=True)
PWD = Path(__file__).resolve().parent.parent.parent


def tools(s):
  b = Path(sys.executable).parent
  need = [
    x
    for x in ("ersilia_model_lint", "ersilia_model_pack", "ersilia_model_serve")
    if not (b / x).exists()
  ]
  if need:
    s.install("-e", str(PWD))
    still = [x for x in need if not (b / x).exists()]
    if still:
      s.error(f"missing: {', '.join(still)}")


def run(s, *args):
  cmd = " ".join(str(a) for a in args)
  s.log(f"→ {cmd}")
  try:
    s.run(*args, external=True)
  except nox.command.CommandFailed as e:
    s.error(f"fail: {cmd}\n{e}")


def shim_bash(s):
  d = PLAY / "shims"
  d.mkdir(parents=True, exist_ok=True)
  p = d / "bash"
  p.write_text('#!/bin/sh\nexec /bin/sh "$@"\n')
  os.chmod(p, 0o755)
  s.env["PATH"] = str(d) + os.pathsep + s.env.get("PATH", "")


def srv_bg(s, exe, bundle, port, log, pidf):
  cmd = f"'{exe}' --bundle_path '{bundle}' --port {port} > '{log}' 2>&1 & echo $! > '{pidf}'"
  s.run("sh", "-c", cmd, external=True)
  if not pidf.exists() or not pidf.read_text().strip().isdigit():
    txt = log.read_text() if log.exists() else ""
    s.error(f"server start failed\n{txt}")
  return int(pidf.read_text().strip())


def srv_kill(s, pid):
  s.run("sh", "-c", f"kill {pid} >/dev/null 2>&1 || true", external=True)


def http(url, data=None, method=None, timeout=60):
  if data is not None and not isinstance(data, (bytes, bytearray)):
    data = json.dumps(data).encode("utf-8")
  headers = {"Content-Type": "application/json"} if data is not None else {}
  req = urllib.request.Request(
    url, data=data, headers=headers, method=method or ("POST" if data else "GET")
  )
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return r.read().decode("utf-8")


def ready(base, secs=30):
  paths = ["/healthz", "/docs", "/"]
  t0 = time.time()
  while time.time() - t0 < secs:
    for p in paths:
      try:
        with urllib.request.urlopen(base + p, timeout=2) as r:
          if r.status < 500:
            return p
      except Exception:
        pass
    time.sleep(1)
  return None


def read_values(path):
  with open(path, "r") as f:
    reader = csv.reader(f)
    next(reader)
    data = [r for r in reader]
  return data


def match(act, exp, tol=1e-1):
  if len(act) != len(exp):
    return False
  for a_row, e_row in zip(act, exp):
    if len(a_row) != len(e_row):
      return False
    for a, e in zip(a_row, e_row):
      if isinstance(a, (int, float)) and isinstance(e, (int, float)):
        if not math.isclose(a, e, rel_tol=tol, abs_tol=tol):
          return False
      else:
        if a != e:
          return False
  return True

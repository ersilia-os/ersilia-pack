import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

import nox

EOS_ROOT = Path.home() / "eos"
ERP_PLAYGROUND = EOS_ROOT / "erp_playground"
ERP_PLAYGROUND.mkdir(parents=True, exist_ok=True)

NOX_PWD = Path(__file__).resolve().parent.parent.parent

MODEL_PY = {
    "eos43at": "3.8",
    "eos4e40": "3.9",
    "eos5axz": "3.10",
    "eos526j": "3.11",
    "eos8a4x": "3.12",
}
print(MODEL_PY)
PY_MATRIX = set(MODEL_PY.values())
DEFAULT_PORT = int(os.environ.get("PORT", "8000"))
DEFAULT_PAYLOAD = Path(os.environ.get("PAYLOAD_FILE", "data/payload.json"))

nox.options.envdir = str(ERP_PLAYGROUND / ".nox")


def ensure_ersilia_tools(session):
    venv_bin = Path(sys.executable).parent
    tools = ["ersilia_model_lint", "ersilia_model_pack", "ersilia_model_serve"]
    missing = [t for t in tools if not (venv_bin / t).exists()]
    if missing:
        session.install("-e", str(NOX_PWD))
        missing = [t for t in tools if not (venv_bin / t).exists()]
        if missing:
            session.error(f"Missing required CLI(s) after install: {', '.join(missing)}")


def run_checked(session, *args):
    cmd = " ".join(str(a) for a in args)
    session.log(f"→ {cmd}")
    try:
        session.run(*args, external=True)
    except nox.command.CommandFailed as e:
        session.error(f"✗ Command failed: {cmd}\n{e}")


def start_server_detached(session, serve_exe: Path, bundle_path: Path, port: int, logfile: Path, pidfile: Path):
    cmd = f"'{serve_exe}' --bundle_path '{bundle_path}' --port {port} > '{logfile}' 2>&1 & echo $! > '{pidfile}'"
    session.run("sh", "-c", cmd, external=True)
    if not pidfile.exists() or not pidfile.read_text().strip().isdigit():
        txt = logfile.read_text() if logfile.exists() else ""
        session.error(f"✗ Failed to start server; no PID written.\nLogs:\n{txt}")
    return int(pidfile.read_text().strip())


def stop_server(session, pid: int):
    session.run("sh", "-c", f"kill {pid} >/dev/null 2>&1 || true", external=True)


def do_model(session, model_id: str, port: int, payload_file: Path, conda_env_name: str):
    logfile = Path(f"{model_id}-serve.log")
    pidfile = Path(f"{model_id}.pid")
    bundles_root = EOS_ROOT / "repository"
    bundle_path = bundles_root / model_id
    base_url = f"http://127.0.0.1:{port}"

    if Path(model_id).exists():
        shutil.rmtree(model_id)
    if bundle_path.exists():
        shutil.rmtree(bundle_path, ignore_errors=True)
    if pidfile.exists():
        pidfile.unlink()
    if logfile.exists():
        logfile.unlink()

    run_checked(session, "git", "clone", "--depth", "1", f"https://github.com/ersilia-os/{model_id}.git")
    run_checked(session, "ersilia_model_lint", "--repo_path", model_id)

    bundles_root.mkdir(parents=True, exist_ok=True)

    shims = ERP_PLAYGROUND / "shims"
    shims.mkdir(parents=True, exist_ok=True)
    bash_shim = shims / "bash"
    bash_shim.write_text('#!/bin/sh\nexec /bin/sh "$@"\n')
    os.chmod(bash_shim, 0o755)
    session.env["PATH"] = str(shims) + os.pathsep + session.env.get("PATH", "")

    run_checked(
        session,
        "ersilia_model_pack",
        "--repo_path", model_id,
        "--bundles_repo_path", str(bundles_root),
        "--conda_env_name", conda_env_name,
    )

    venv_bin = Path(sys.executable).parent
    serve_exe = venv_bin / "ersilia_model_serve"
    if not serve_exe.exists():
        session.error(f"✗ Unable to locate ersilia_model_serve at {serve_exe}")

    logfile.touch()
    pid = start_server_detached(session, serve_exe, bundle_path, port, logfile, pidfile)

    ok, start_ts = False, time.time()
    while time.time() - start_ts < 30:
        try:
            with urllib.request.urlopen(f"{base_url}/healthz", timeout=2) as r:
                if r.status == 200:
                    ok = True
                    break
        except Exception:
            time.sleep(1)
    if not ok:
        txt = logfile.read_text() if logfile.exists() else ""
        stop_server(session, pid)
        session.error(f"✗ Server did not become healthy in time.\nLogs:\n{txt}")

    if not payload_file.exists():
        stop_server(session, pid)
        session.error(f"✗ Payload file not found: {payload_file}")

    data = json.loads(payload_file.read_text())
    req = urllib.request.Request(
        f"{base_url}/run",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except Exception as e:
        txt = logfile.read_text() if logfile.exists() else ""
        stop_server(session, pid)
        session.error(f"✗ /run failed: {e}\nLogs:\n{txt}")

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        txt = logfile.read_text() if logfile.exists() else ""
        stop_server(session, pid)
        session.error(f"✗ Non-JSON response from /run\nRaw:\n{body}\nLogs:\n{txt}")

    print(json.dumps(parsed, indent=2))

    interval = int(os.environ.get("JOB_POLL_INTERVAL", "2"))
    timeout = int(os.environ.get("JOB_POLL_TIMEOUT", "120"))

    submit_req = urllib.request.Request(
        f"{base_url}/job/submit",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(submit_req, timeout=60) as resp:
            submit_body = resp.read().decode("utf-8")
    except Exception as e:
        txt = logfile.read_text() if logfile.exists() else ""
        stop_server(session, pid)
        session.error(f"✗ /job/submit failed: {e}\nLogs:\n{txt}")

    try:
        submit_json = json.loads(submit_body)
        job_id = submit_json.get("job_id")
    except Exception:
        stop_server(session, pid)
        session.error(f"✗ /job/submit returned non-JSON\nRaw:\n{submit_body}")

    if not job_id or job_id == "null":
        stop_server(session, pid)
        session.error(f"✗ Invalid job_id from /job/submit\nPayload:\n{submit_body}")

    start_poll = time.time()
    last_status = None
    while time.time() - start_poll < timeout:
        try:
            with urllib.request.urlopen(f"{base_url}/job/status/{job_id}", timeout=10) as resp:
                status_body = resp.read().decode("utf-8")
            status_json = json.loads(status_body)
            last_status = status_json.get("status")
            print(f"[{int(time.time()-start_poll)}s] status = {last_status}")
            if last_status == "completed":
                break
            if last_status == "failed":
                txt = logfile.read_text() if logfile.exists() else ""
                stop_server(session, pid)
                session.error(f"✗ Job failed\nStatus payload:\n{status_body}\nLogs:\n{txt}")
        except Exception as e:
            txt = logfile.read_text() if logfile.exists() else ""
            stop_server(session, pid)
            session.error(f"✗ /job/status error: {e}\nLogs:\n{txt}")
        time.sleep(interval)

    if last_status != "completed":
        txt = logfile.read_text() if logfile.exists() else ""
        stop_server(session, pid)
        session.error(f"✗ Timeout ({timeout}s) without completion\nLogs:\n{txt}")

    try:
        with urllib.request.urlopen(f"{base_url}/job/result/{job_id}", timeout=30) as resp:
            result_body = resp.read().decode("utf-8")
    except Exception as e:
        txt = logfile.read_text() if logfile.exists() else ""
        stop_server(session, pid)
        session.error(f"✗ /job/result error: {e}\nLogs:\n{txt}")

    try:
        result_json = json.loads(result_body)
    except json.JSONDecodeError:
        stop_server(session, pid)
        session.error(f"✗ /job/result returned non-JSON\nRaw:\n{result_body}")

    print(json.dumps(result_json, indent=2))
    stop_server(session, pid)


def run_for_models(session, models, base_port, payload_file):
    ensure_ersilia_tools(session)
    venv_bin = Path(sys.executable).parent
    session.env["PATH"] = str(venv_bin) + os.pathsep + session.env.get("PATH", "")
    for i, model in enumerate(models):
        port = base_port + i
        conda_env_name = model
        do_model(session, model_id=model, port=port, payload_file=payload_file, conda_env_name=conda_env_name)


@nox.session(venv_backend="conda", python=PY_MATRIX, reuse_venv=True)
def ci(session: nox.Session):
    current_py = f"{sys.version_info.major}.{sys.version_info.minor}"
    port = DEFAULT_PORT
    payload_file = DEFAULT_PAYLOAD

    args = [a for a in session.posargs if not a.endswith(".json") and not a.isdigit()]
    for a in session.posargs:
        if a.isdigit():
            port = int(a)
        elif a.endswith(".json"):
            payload_file = Path(a)

    requested_models = list(MODEL_PY.keys())
    requested_py = list(PY_MATRIX)
    print(requested_models, requested_py)

    if requested_models and requested_py:
        target_models = [m for m in requested_models if MODEL_PY[m] in requested_py]
    elif requested_models:
        target_models = requested_models
    elif requested_py:
        target_models = [m for m, v in MODEL_PY.items() if v in requested_py]
    else:
        target_models = list(MODEL_PY.keys())

    target_models = [m for m in target_models]
    if not target_models:
        session.log(f"skip: no models mapped to python {current_py}")
        return

    run_for_models(session, target_models, port, payload_file)


for _model, _py in MODEL_PY.items():
    def _make_model_session(model_id=_model, py=_py):
        @nox.session(name=f"ci-{model_id}", venv_backend="conda", python=py, reuse_venv=True)
        def _sess(session: nox.Session):
            run_for_models(session, [model_id], DEFAULT_PORT, DEFAULT_PAYLOAD)
    _make_model_session()

for _model, _py in MODEL_PY.items():
    alias = f"py{_py.replace('.', '')}"
    def _make_py_session(py=_py):
        @nox.session(name=f"ci-{alias}", venv_backend="conda", python=py, reuse_venv=True)
        def _sess(session: nox.Session):
            models = [m for m, v in MODEL_PY.items() if v == py]
            run_for_models(session, models, DEFAULT_PORT, DEFAULT_PAYLOAD)
    _make_py_session()

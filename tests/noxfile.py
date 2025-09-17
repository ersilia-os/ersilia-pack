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
nox.options.envdir = str(ERP_PLAYGROUND / ".nox")


def ensure_rdkit(session):
    try:
        session.run("python", "-c", "import rdkit", silent=True)
    except Exception:
        session.install("--upgrade", "pip", "setuptools", "wheel")
        session.install("rdkit-pypi")


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
    cmd = (
        f"'{serve_exe}' --bundle_path '{bundle_path}' --port {port} "
        f"> '{logfile}' 2>&1 & echo $! > '{pidfile}'"
    )
    session.run("sh", "-c", cmd, external=True)
    if not pidfile.exists() or not pidfile.read_text().strip().isdigit():
        txt = logfile.read_text() if logfile.exists() else ""
        session.error(f"✗ Failed to start server; no PID written.\nLogs:\n{txt}")
    return int(pidfile.read_text().strip())


def stop_server(session, pid: int):
    session.run("sh", "-c", f"kill {pid} >/dev/null 2>&1 || true", external=True)


@nox.session(venv_backend="virtualenv", python="3.10", reuse_venv=True)
def ci(session: nox.Session):
    model_id = session.posargs[0] if len(session.posargs) >= 1 else "eos3b5e"
    port = int(session.posargs[1]) if len(session.posargs) >= 2 else 8000
    payload_file = Path(session.posargs[2]) if len(session.posargs) >= 3 else Path("data/payload.json")

    logfile = Path(f"{model_id}-serve.log")
    pidfile = Path(f"{model_id}.pid")
    bundles_root = EOS_ROOT / "repository"
    bundle_path = bundles_root / model_id
    base_url = f"http://127.0.0.1:{port}"

    ensure_rdkit(session)
    ensure_ersilia_tools(session)

    venv_bin = Path(sys.executable).parent
    session.env["PATH"] = str(venv_bin) + os.pathsep + session.env.get("PATH", "") + os.pathsep + "/bin:/usr/bin"
    session.env["PIP_REQUIRE_VIRTUALENV"] = "1"

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
    run_checked(session, "ersilia_model_pack", "--repo_path", model_id, "--bundles_repo_path", str(bundles_root))

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

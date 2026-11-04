import sys
import textwrap

import pytest

from src.ersilia_pack.templates import warm


WARM_MAIN = """
import csv, os, sys

LOADS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loads.txt")


def load_tool():
    with open(LOADS_FILE, "a") as f:
        f.write("load\\n")
    print("noise on stdout from load")
    return {"factor": 2}


def run_tool(model, input_file, output_file):
    print("noise on stdout from run")
    with open(input_file) as f:
        rows = list(csv.reader(f))[1:]
    if rows and rows[0][0] == "fail":
        raise ValueError("bad input")
    if rows and rows[0][0] == "exit":
        sys.exit(3)
    if rows and rows[0][0] == "crash":
        os._exit(1)
    with open(output_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["value"])
        for r in rows:
            w.writerow([len(r[0]) * model["factor"]])


if __name__ == "__main__":
    run_tool(load_tool(), sys.argv[1], sys.argv[2])
"""

COLD_MAIN = """
import sys
input_file = sys.argv[1]
"""


def _write(path, content):
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(textwrap.dedent(content))


@pytest.fixture
def framework(tmp_path, monkeypatch):
  fw = tmp_path / "framework"
  _write(fw / "code" / "main.py", WARM_MAIN)
  _write(fw / "run.sh", f"{sys.executable} $1/code/main.py $2 $3\n")
  monkeypatch.setattr(warm, "FRAMEWORK_FOLDER", str(fw))
  monkeypatch.setattr(warm, "MAIN_PY", str(fw / "code" / "main.py"))
  monkeypatch.setattr(warm, "RUN_SH", str(fw / "run.sh"))
  monkeypatch.delenv(warm.WARM_ENV_VAR, raising=False)
  return fw


def _batch(tmp_path, name, items):
  in_f = tmp_path / f"in-{name}.csv"
  in_f.write_text("input\n" + "".join(f"{i}\n" for i in items))
  return str(in_f), str(tmp_path / f"out-{name}.csv")


def _loads(fw):
  path = fw / "code" / "loads.txt"
  return path.read_text().count("load") if path.exists() else 0


class TestDetection:
  def test_warm_model_detected(self, framework):
    assert warm.detect_python() == sys.executable

  def test_script_main_stays_cold(self, framework):
    _write(framework / "code" / "main.py", COLD_MAIN)
    assert warm.detect_python() is None

  def test_plain_load_and_run_names_stay_cold(self, framework):
    # Only load_tool/run_tool opt in; a main.py that happens to define
    # load/run must keep the run.sh path.
    _write(
      framework / "code" / "main.py",
      "def load():\n    return None\n\ndef run(model, i, o):\n    pass\n",
    )
    assert warm.detect_python() is None

  @pytest.mark.parametrize(
    "run_sh",
    [
      "cd $1/code\npython main.py $2 $3\n",
      "python $1/code/main.py $2 $3 --gpu\n",
      "python $1/code/other.py $2 $3\n",
    ],
  )
  def test_custom_run_sh_stays_cold(self, framework, run_sh):
    _write(framework / "run.sh", run_sh)
    assert warm.detect_python() is None

  def test_comments_and_blank_lines_allowed(self, framework):
    _write(framework / "run.sh", "#!/bin/bash\n\npython $1/code/main.py $2 $3")
    assert warm.detect_python() == "python"

  def test_env_var_disables(self, framework, monkeypatch):
    monkeypatch.setenv(warm.WARM_ENV_VAR, "0")
    assert warm.detect_python() is None


class TestWarmWorker:
  def test_loads_once_across_batches(self, framework, tmp_path):
    worker = warm.WarmWorker(sys.executable)
    try:
      for n in range(3):
        in_f, out_f = _batch(tmp_path, n, ["C", "CCO"])
        worker.run(in_f, out_f)
        assert open(out_f).read().split() == ["value", "2", "6"]
      assert _loads(framework) == 1
    finally:
      worker.close()

  def test_model_error_keeps_worker_loaded(self, framework, tmp_path):
    worker = warm.WarmWorker(sys.executable)
    try:
      for bad in ["fail", "exit"]:
        in_f, out_f = _batch(tmp_path, bad, [bad])
        with pytest.raises(warm.WarmRunError):
          worker.run(in_f, out_f)
      in_f, out_f = _batch(tmp_path, "ok", ["CC"])
      worker.run(in_f, out_f)
      assert _loads(framework) == 1
    finally:
      worker.close()

  def test_crash_restarts_on_next_batch(self, framework, tmp_path):
    worker = warm.WarmWorker(sys.executable)
    try:
      in_f, out_f = _batch(tmp_path, "crash", ["crash"])
      with pytest.raises(warm.WarmWorkerDied):
        worker.run(in_f, out_f)
      in_f, out_f = _batch(tmp_path, "ok", ["CC"])
      worker.run(in_f, out_f)
      assert _loads(framework) == 2
    finally:
      worker.close()

  def test_model_modules_not_shadowed_by_app(self, framework, tmp_path):
    # The worker lives next to the server's utils.py. A model's utils folder
    # without __init__.py (a namespace package) loses to any utils.py on sys.path,
    # so the server's folder must not be there.
    _write(framework / "code" / "utils" / "helper.py", "VALUE = 'model utils'\n")
    _write(
      framework / "code" / "main.py",
      "def load_tool():\n    from utils.helper import VALUE\n    return VALUE\n\n"
      "def run_tool(model, i, o):\n    open(o, 'w').write(model)\n",
    )
    worker = warm.WarmWorker(sys.executable)
    try:
      in_f, out_f = _batch(tmp_path, "u", ["C"])
      worker.run(in_f, out_f)
      assert open(out_f).read() == "model utils"
    finally:
      worker.close()

  def test_load_failure_disables(self, framework, tmp_path):
    _write(
      framework / "code" / "main.py",
      "def load_tool():\n    raise RuntimeError('no checkpoints')\n\n"
      "def run_tool(model, i, o):\n    pass\n",
    )
    worker = warm.WarmWorker(sys.executable)
    assert worker.ensure_loaded() is False
    in_f, out_f = _batch(tmp_path, "x", ["C"])
    with pytest.raises(warm.WarmWorkerDied):
      worker.run(in_f, out_f)


class TestRunFramework:
  def test_falls_back_to_run_sh_when_cold(self, framework, tmp_path, monkeypatch):
    monkeypatch.setattr(warm, "_worker", None)
    in_f, out_f = _batch(tmp_path, "cold", ["CCC"])
    warm.run_framework(in_f, out_f)
    assert open(out_f).read().split() == ["value", "6"]
    assert _loads(framework) == 1

  def test_falls_back_to_run_sh_when_worker_dies(
    self, framework, tmp_path, monkeypatch
  ):
    worker = warm.WarmWorker(sys.executable)
    monkeypatch.setattr(warm, "_worker", worker)
    try:
      worker.ensure_loaded()
      worker.proc.kill()
      worker.proc.wait()
      monkeypatch.setattr(worker, "_start", lambda: setattr(worker, "disabled", True))
      in_f, out_f = _batch(tmp_path, "fb", ["CC"])
      warm.run_framework(in_f, out_f)
      assert open(out_f).read().split() == ["value", "4"]
    finally:
      worker.close()

  def test_start_uses_worker_and_stop_closes_it(self, framework, tmp_path, monkeypatch):
    monkeypatch.setattr(warm, "_worker", None)
    warm.start()
    try:
      assert warm.is_active()
      warm.get_worker().ensure_loaded()
      assert warm.is_loaded()
      for n in range(2):
        in_f, out_f = _batch(tmp_path, n, ["CO"])
        warm.run_framework(in_f, out_f)
      assert _loads(framework) == 1
      proc = warm.get_worker().proc
    finally:
      warm.stop()
    assert proc.poll() is not None
    assert not warm.is_loaded()


class TestStatus:
  def test_reports_memory_held_by_loaded_model(self, framework, monkeypatch):
    # load_tool() keeps ~60 MB alive; the reported memory must include it.
    _write(
      framework / "code" / "main.py",
      "def load_tool():\n    return bytearray(60 * 1024 * 1024)\n\n"
      "def run_tool(model, i, o):\n    pass\n",
    )
    monkeypatch.setattr(warm, "_worker", None)
    warm.start()
    try:
      warm.get_worker().ensure_loaded()
      info = warm.status()
      assert info["active"] and info["loaded"]
      assert info["loadSeconds"] >= 0
      assert info["memoryAfterLoadMb"] >= 60
      assert info["memoryMb"] >= 60
      assert info["pid"] == warm.get_worker().proc.pid
      if sys.platform.startswith("linux"):
        assert info["peakMemoryMb"] >= 60
    finally:
      warm.stop()
    assert warm.status()["memoryMb"] is None

  def test_cold_model_reports_inactive(self, framework, monkeypatch):
    _write(framework / "code" / "main.py", COLD_MAIN)
    monkeypatch.setattr(warm, "_worker", None)
    warm.start()
    assert warm.status() == {"active": False, "loaded": False}

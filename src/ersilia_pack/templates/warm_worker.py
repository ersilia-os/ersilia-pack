# Long-lived worker that keeps a model loaded between batches.
#
# Runs in the model's own Python (the interpreter named in run.sh), so it must
# only use the standard library and stay compatible with Python 3.8.
#
# Usage: python warm_worker.py <path/to/main.py>
#
# main.py must define load() and run(model, input_file, output_file).
# Protocol (one JSON object per line):
#   worker -> server, once: {"status": "ready"} or {"status": "error", "error": ...}
#   server -> worker:       {"input": <path>, "output": <path>}
#   worker -> server:       {"ok": true} or {"ok": false, "error": ...}
# The worker exits when its stdin is closed, i.e. when the server goes away.

import importlib.util
import json
import os
import sys
import traceback


def _protocol_streams():
  # Keep private copies of stdin/stdout for the protocol, then point fds 0/1 at
  # /dev/null and stderr, so anything the model prints (even from C code) goes
  # to the server log instead of corrupting the protocol.
  proto_in = os.fdopen(os.dup(0), "r")
  proto_out = os.fdopen(os.dup(1), "w")
  devnull = os.open(os.devnull, os.O_RDONLY)
  os.dup2(devnull, 0)
  os.close(devnull)
  os.dup2(2, 1)
  return proto_in, proto_out


def _send(stream, message):
  stream.write(json.dumps(message) + "\n")
  stream.flush()


def _import_main(main_path):
  # Mimic `python main.py`: the code folder is first on sys.path so sibling
  # imports resolve. The module is not named __main__, so the script's
  # `if __name__ == "__main__":` block does not run.
  # Python put this script's folder (the server's app/) on sys.path. Drop it, or
  # its utils.py, main.py, etc. would shadow the model's own modules.
  here = os.path.dirname(os.path.abspath(__file__))
  sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != here]
  sys.path.insert(0, os.path.dirname(main_path))
  sys.argv = [main_path]
  spec = importlib.util.spec_from_file_location("main", main_path)
  module = importlib.util.module_from_spec(spec)
  sys.modules["main"] = module
  spec.loader.exec_module(module)
  return module


def main():
  main_path = os.path.abspath(sys.argv[1])
  proto_in, proto_out = _protocol_streams()
  try:
    module = _import_main(main_path)
    model = module.load()
  except BaseException:
    _send(proto_out, {"status": "error", "error": traceback.format_exc()})
    return 1
  _send(proto_out, {"status": "ready"})

  for line in proto_in:
    if not line.strip():
      continue
    request = json.loads(line)
    try:
      module.run(model, request["input"], request["output"])
      _send(proto_out, {"ok": True})
    except BaseException:
      # SystemExit from the model is reported as an error, not obeyed, so one
      # bad batch does not take the loaded model down with it.
      _send(proto_out, {"ok": False, "error": traceback.format_exc()})
  return 0


if __name__ == "__main__":
  sys.exit(main())

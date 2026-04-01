import argparse
import os
import subprocess
import sys

from .utils import find_free_port, logger


class BundleServer(object):
  def __init__(self, bundle_path, host, port, root_path=""):
    self.bundle_path = os.path.abspath(bundle_path)
    self._resolve_bundle_path()
    self.host = host
    if port is None:
      port = find_free_port(self.host)
    self.port = port
    self.root_path = root_path

  def _resolve_bundle_path(self):
    subfolders = os.listdir(self.bundle_path)
    if len(subfolders) == 1 and os.path.isdir(
      os.path.join(self.bundle_path, subfolders[0])
    ):
      self.bundle_path = os.path.join(self.bundle_path, subfolders[0])

  def serve(self):
    logger.info("Serving the app from system Python")
    cmd = "{0} {1}/run_uvicorn.py --host {2} --port {3}".format(
      sys.executable, self.bundle_path, self.host, self.port
    )
    if self.root_path:
      cmd += " --root-path {0}".format(self.root_path)
    logger.info(cmd)
    cmd = [
      sys.executable,
      "{0}/run_uvicorn.py".format(self.bundle_path),
      "--host",
      self.host,
      "--port",
      str(self.port),
    ]
    if self.root_path:
      cmd += ["--root-path", self.root_path]
    subprocess.run(cmd, check=True)
    logger.info("App served successfully")


def main():
  parser = argparse.ArgumentParser(description="ErsiliaAPI app server")
  parser.add_argument(
    "--bundle_path",
    required=True,
    type=str,
    help="Path to the model repository",
  )
  parser.add_argument(
    "--host",
    default="0.0.0.0",
    type=str,
    help="Host URL",
  )
  parser.add_argument(
    "--port",
    default=None,
    type=int,
    help="An integer for the port",
  )
  parser.add_argument(
    "--root-path",
    "--root_path",
    dest="root_path",
    default=os.getenv("ROOT_PATH", ""),
    type=str,
    help="ASGI root_path for deployments behind a stripped path prefix",
  )
  args = parser.parse_args()
  bs = BundleServer(args.bundle_path, args.host, args.port, args.root_path)
  bs.serve()


if __name__ == "__main__":
  main()

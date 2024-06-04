import os
import argparse
import json
import subprocess
import sys
from .utils import find_free_port


class BundleServer(object):
    def __init__(self, bundle_path, host, port):
        self.bundle_path = os.path.abspath(bundle_path)
        self._resolve_bundle_path()
        self.host = host
        if port is None:
            port = find_free_port(self.host)
        self.port = port
        self.conda = self._is_conda()

    def _resolve_bundle_path(self):
        subfolders = os.listdir(self.bundle_path)
        if len(subfolders) == 1 and os.path.isdir(os.path.join(self.bundle_path, subfolders[0])):
            self.bundle_path = os.path.join(self.bundle_path, subfolders[0])

    def _is_conda(self):
        with open(os.path.join(self.bundle_path, "environment_mode.json")) as f:
            data = json.load(f)
        if data["mode"] == "conda":
            return True
        else:
            return False

    def serve_system(self):
        print("Serving the app from system Python")
        cmd = "{0} {1}/run_uvicorn.py --host {2} --port {3}".format(
            sys.executable, self.bundle_path, self.host, self.port
        )
        print(cmd)
        cmd = [
            sys.executable,
            "{0}/run_uvicorn.py".format(self.bundle_path),
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]
        subprocess.run(cmd, check=True)
        print("App served successfully")

    def serve_conda(self):
        # TODO: Implement the conda environment activation
        pass

    def serve(self):
        if self.conda:
            self.serve_conda()
        else:
            self.serve_system()


def main():
    parser = argparse.ArgumentParser(description="ErsiliaAPI app server")
    parser.add_argument(
        "--bundle_path", required=True, type=str, help="Path to the model repository"
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
    args = parser.parse_args()
    bs = BundleServer(args.bundle_path, args.host, args.port)
    bs.serve()


if __name__ == "__main__":
    main()

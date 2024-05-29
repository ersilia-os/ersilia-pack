import os
import argparse
import json
import uvicorn


class BundleServer(object):
    def __init__(self, bundle_path, host, port):
        self.bundle_path = bundle_path
        self.host = host
        self.port = port
        self.conda = self._is_conda()

    def _is_conda(self):
        with open(os.path.join(self.bundle_path, "environment_mode.json")) as f:
            data = json.load(f)
        if data["mode"] == "conda":
            return True
        else:
            return False

    def serve_system(self):
        uvicorn.run(
            "app:app",
            host=self.host,
            port=self.port,
            reload=True,
            app_dir=self.bundle_path,
        )

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
        default=8000,
        type=int,
        help="An integer for the port",
    )
    args = parser.parse_args()
    print(args)
    bs = BundleServer(args.bundle_path, args.host, args.port)
    bs.serve()


if __name__ == "__main__":
    main()

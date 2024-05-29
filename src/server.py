import argparse
import uvicorn


class BundleServer(object):
    def __init__(self, bundle_path, host, port):
        self.bundle_path = bundle_path
        self.host = host
        self.port = port

    def serve(self):
        uvicorn.run(
            "app:app",
            host=self.host,
            port=self.port,
            reload=True,
            app_dir=self.bundle_path,
        )


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

import os
import argparse
import uvicorn

root = os.path.dirname(os.path.abspath(__file__))
framework_folder = os.path.join(root, "model", "framework")


def main():
    parser = argparse.ArgumentParser(description="Ersilia API app")
    parser.add_argument("--port", default=8000, type=int, help="An integer for the port")
    parser.add_argument("--host", default="0.0.0.0", type=str, help="Host URL")
    args = parser.parse_args()
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=True, reload_dirs=[framework_folder, os.path.join(root, "app")])


if __name__ == "__main__":
    main()
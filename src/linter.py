import os
import json
import argparse


class SimpleModelLinter(object):
    def __init__(self, model_id, repo_path):
        self.model_id = model_id
        self.repo_path = repo_path

    def _check_model_id(self):
        if not self.model_id.startswith("eos") or len(self.model_id) != 7:
            raise Exception("Model identifier is not correct")

    def _check_examples(self):
        if not os.path.exists(
            os.path.join(self.repo_path, "model", "framework", "example_input.csv")
        ):
            raise Exception("example_input.csv not found")
        if not os.path.exists(
            os.path.join(self.repo_path, "model", "framework", "example_output.csv")
        ):
            raise Exception("example_output.csv not found")

    def _check_metadata(self):
        if not os.path.exists(os.path.join(self.repo_path, "metadata.json")):
            raise Exception("metadata.json not found")
        with open(os.path.join(self.repo_path, "metadata.json")) as f:
            metadata = json.load(f)
        if "model_id" not in metadata:
            raise Exception("model_id not found in metadata.json")

    def check(self):
        self._check_model_id()
        self._check_examples()
        self._check_metadata()
        print("Model {0} is valid".format(self.model_id))


def main():
    parser = argparse.ArgumentParser(description="ErsiliaAPI app")
    parser.add_argument(
        "--model_id", required=True, type=str, help="Ersilia model identifier"
    )
    parser.add_argument(
        "--repo_path", required=True, type=str, help="Path to the model repository"
    )
    args = parser.parse_args()
    sml = SimpleModelLinter(args.model_id, args.repo_path)
    sml.check()

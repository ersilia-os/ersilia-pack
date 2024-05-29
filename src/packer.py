import os
import shutil
import argparse
import datetime
import uuid
import subprocess

root = os.path.dirname(os.path.abspath(__file__))


class FastApiAppPacker(object):
    def __init__(self, model_id, repo_path):
        self.model_id = model_id
        self.dest_dir = repo_path
        if not os.path.exists(self.dest_dir):
            raise Exception("Model path {0} does not exist".format(self.dest_dir))
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        timestamp = timestamp + "-" + str(uuid.uuid4())
        self.bundle_dir = os.path.abspath(
            os.path.join(self.dest_dir, "..", "repository", self.model_id)
        )
        if os.path.exists(self.bundle_dir):
            print("Folder {0} existed. Removing it".format(self.bundle_dir))
            shutil.rmtree(self.bundle_dir)
        self.bundle_dir = os.path.join(self.bundle_dir, timestamp)
        os.makedirs(self.bundle_dir)

    def _create_bundle_structure(self):
        shutil.copy(
            os.path.join(self.dest_dir, "metadata.json"),
            os.path.join(self.bundle_dir, "metadata.json"),
        )
        shutil.copytree(
            os.path.join(self.dest_dir, "model"), os.path.join(self.bundle_dir, "model")
        )
        shutil.copy(
            os.path.join(self.bundle_dir, "metadata.json"),
            os.path.join(self.bundle_dir, "info.json"),
        )

    def _get_api_names(self):
        api_names = []
        for l in os.listdir(os.path.join(self.bundle_dir, "model", "framework")):
            if l.endswith(".sh"):
                api_names += [l.split(".sh")[0]]
        if len(api_names) == 0:
            raise Exception("No API names found. An API should be a .sh file")
        return api_names

    def _create_app_file(self):
        api_names = self._get_api_names()
        shutil.copy(
            os.path.join(root, "utils", "app_template.py"),
            os.path.join(self.bundle_dir, "app.py"),
        )
        # TODO: It should incorporate all the API endpoints that are necessary (beyond 'run')

    def _install_packages(self):
        cmd = "bash {0}/install.sh".format(self.dest_dir)
        subprocess.Popen(cmd, shell=True).wait()

    def pack(self):
        self._create_bundle_structure()
        self._create_app_file()
        self._install_packages()


def main():
    parser = argparse.ArgumentParser(description="ErsiliaAPI app")
    parser.add_argument(
        "--model_id", required=True, type=str, help="Ersilia model identifier"
    )
    parser.add_argument(
        "--repo_path", required=True, type=str, help="Path to the model repository"
    )
    args = parser.parse_args()
    fp = FastApiAppPacker(args.model_id, args.repo_path)
    fp.pack()


if __name__ == "__main__":
    main()

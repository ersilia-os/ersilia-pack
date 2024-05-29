from ersilia import ErsiliaBase
import os
import shutil
import datetime

root = os.path.dirname(os.path.abspath(__file__))


class FastApiAppPacker(ErsiliaBase):
    def __init__(self, model_id, repo_path):
        self.model_id = model_id
        self.dest_dir = repo_path
        if not os.path.exist(self.dest_dir):
            raise Exception("Model path {0} does not exist".format(self.dest_dir))
        timestamp = "foo"  # TODO put timestamp
        self.bundle_dir = os.path.abspath(
            os.path.join(self.dest_dir, "..", "repository", self.model_id)
        )
        if os.path.exists(self.bundle_dir):
            print("Folder {0} existed. Removing it")
            shutil.rmtree(self.bundle_dir)
        self.bundle_dir = os.path.join(self.bundle_dir, timestamp)
        os.makedirs(self.bundle_dir)
        print("Created folder {0}".format(self.bundle_dir))

    def _create_bundle_structure(self):
        shutil.copy(
            os.path.join(self.dest_dir, "metadata.json"),
            os.path.join(self.bundle_dir, "metadata.json"),
        )
        shutil.copy(
            os.path.join(self.dest_dir, "model"), os.path.join(self.bundle_dir, "model")
        )
        shutil.copy(
            os.path.join(self.bundle_dir, "metadata.json"),
            os.path.join(self.bundle_dir, "info.json"),
        )

    def _get_api_names(self):
        api_names = []
        for l in os.path.listdir(os.path.join(self.bundle_dir, "model", "framework")):
            if l.endswith(".sh"):
                api_names += [l.split(".sh")[0]]
        if len(api_names) == 0:
            raise Exception("No API names found. An API should be a .sh file")
        return api_names

    def _create_app_file(self):
        api_names = self._get_api_names()
        os.copy(
            os.path.join(root, "app_template.py"),
            os.path.join(self.bundle_dir, "app.py"),
        )
        # TODO: It should incorporate all the API endpoints that are necessary (beyond 'run')

    def pack(self):
        self._create_bundle_structure()
        self._create_app_file()


if __name__ == "__main__":
    fp = FastApiAppPacker()
    fp.pack()

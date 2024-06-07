import os
import shutil
import argparse
import datetime
import uuid
import subprocess
import json
import urllib.request

root = os.path.dirname(os.path.abspath(__file__))


class FastApiAppPacker(object):
    def __init__(self, repo_path, bundles_repo_path):
        self.dest_dir = repo_path
        self.bundles_repo_path = bundles_repo_path
        if not os.path.exists(self.dest_dir):
            raise Exception("Model path {0} does not exist".format(self.dest_dir))
        self.model_id = self._get_model_id()
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        timestamp = timestamp + "-" + str(uuid.uuid4())
        self.bundle_dir = os.path.abspath(
            os.path.join(self.bundles_repo_path, self.model_id)
        )
        if os.path.exists(self.bundle_dir):
            print("Folder {0} existed. Removing it".format(self.bundle_dir))
            shutil.rmtree(self.bundle_dir)
        self.bundle_dir = os.path.join(self.bundle_dir, timestamp)
        os.makedirs(self.bundle_dir)

    def _get_model_id(self):
        with open(os.path.join(self.dest_dir, "metadata.json")) as f:
            data = json.load(f)
        return data["Identifier"]

    def _get_favicon(self):
        dest_folder = os.path.join(self.bundle_dir, "static")
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
        url = "https://raw.githubusercontent.com/ersilia-os/ersilia-pack/main/assets/favicon.ico"
        # Extract the file name from the URL
        file_name = os.path.basename(url)
        file_path = os.path.join(dest_folder, file_name)

        try:
            # Download the file from the URL
            urllib.request.urlretrieve(url, file_path)
            print(f"File downloaded and saved to {file_path}")
        except Exception as e:
            print(f"Failed to download file. Error: {e}")

    def _create_bundle_structure(self):
        print("Copying metadata")
        shutil.copy(
            os.path.join(self.dest_dir, "metadata.json"),
            os.path.join(self.bundle_dir, "metadata.json"),
        )
        print("Copying model")
        shutil.copytree(
            os.path.join(self.dest_dir, "model"), os.path.join(self.bundle_dir, "model")
        )
        print("Copying the favicon")

    def _get_info(self):
        print("Getting info from metadata")
        with open(os.path.join(self.bundle_dir, "metadata.json"), "r") as f:
            data = json.load(f)
        info = {}
        info["model_id"] = data["Identifier"]
        info["slug"] = data["Slug"]
        api_list = self._get_api_names_from_sh()
        if api_list is None:
            api_list = self._get_api_names_from_artifact()
        info["api_list"] = api_list
        with open(os.path.join(self.bundle_dir, "info.json"), "w") as f:
            json.dump(info, f, indent=4)
        self.info = info

    def _get_input_schema(self):
        print(self.info)
        input_entity = self.info["card"]["Input"]
        if len(input_entity) > 1:
            return
        input_entity = input_entity[0].lower().replace(" ", "_")
        input_shape = self.info["card"]["Input Shape"].lower().replace(" ", "_")
        shutil.copy(
            os.path.join(
                root, "templates", "input_schemas", input_entity, input_shape + ".py"
            ),
            os.path.join(self.bundle_dir, "app", "input_schema.py"),
        )

    def _get_api_names_from_sh(self):
        api_names = []
        for l in os.listdir(os.path.join(self.bundle_dir, "model", "framework")):
            if l.endswith(".sh"):
                api_names += [l.split(".sh")[0]]
        if len(api_names) == 0:
            raise Exception("No API names found. An API should be a .sh file")
        return api_names
    
    def _get_api_names_from_artifact(self):
        # TODO: Implement this method
        api_names = []
        return api_names

    def _create_app_files(self):
        if not os.path.exists(os.path.join(self.bundle_dir, "app")):
            os.makedirs(os.path.join(self.bundle_dir, "app"))
        shutil.copy(
            os.path.join(root, "templates", "app.py"),
            os.path.join(self.bundle_dir, "app", "main.py"),
        )
        init_file_path = os.path.join(self.bundle_dir, "app", "__init__.py")
        with open(init_file_path, "w") as f:
            pass
        shutil.copy(
            os.path.join(root, "templates", "run_uvicorn.py"),
            os.path.join(self.bundle_dir, "run_uvicorn.py"),
        )
        shutil.copy(
            os.path.join(root, "templates", "utils.py"),
            os.path.join(self.bundle_dir, "app", "utils.py"),
        )

    def _edit_post_commands_app(self):
        api_names = self._get_api_names_from_sh()
        if len(api_names) > 0:
            with open(os.path.join(self.bundle_dir, "app", "main.py"), "r") as f:
                lines = f.readlines()
                lines += ["\n"]
                body_txt = "\n".join(lines)
                for api_name in api_names:
                    with open(os.path.join(root, "templates", "post_code_chunks", "sh_files.txt"), "r") as g:
                        txt = g.read()
                        txt = txt.replace("$$$API_NAME$$$", api_name)
                    txt += "\n"
                    body_txt += txt
            with open(os.path.join(self.bundle_dir, "app", "main.py"), "w") as f:
                f.write(body_txt)
            return
        api_names = self._get_api_names_from_artifact()
        if len(api_names) > 0:
            print("API names from artifact")
            # TODO

    def _convert_dockerfile_to_install_file_if_needed(self):
        # TODO: This method should be improved to handle more complex Dockerfiles
        dockerfile_path = os.path.join(self.dest_dir, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            print("Dockerfile does not exist")
            return
        if os.path.exists(os.path.join(self.dest_dir, "installs", "install.sh")):
            print("Install file already exists")
            return
        with open(dockerfile_path) as f:
            lines = f.readlines()
        install_lines = []
        for l in lines:
            if l.startswith("RUN"):
                install_lines += [l[4:]]
        if not os.path.exists(os.path.join(self.dest_dir, "installs")):
            os.makedirs(os.path.join(self.dest_dir, "installs"))
        with open(os.path.join(self.dest_dir, "installs", "install.sh"), "w") as f:
            f.write("\n".join(install_lines))

    def _install_packages(self):
        cmd = "bash {0}/installs/install.sh".format(self.dest_dir)
        subprocess.Popen(cmd, shell=True).wait()

    def pack(self):
        self._create_bundle_structure()
        self._get_favicon()
        self._create_app_files()
        self._edit_post_commands_app()
        self._get_input_schema()
        self._convert_dockerfile_to_install_file_if_needed()
        self._get_info()
        self._install_packages()


def main():
    parser = argparse.ArgumentParser(description="ErsiliaAPI app")
    parser.add_argument(
        "--repo_path", required=True, type=str, help="Path to the model repository"
    )
    parser.add_argument(
        "--bundles_repo_path",
        required=True,
        type=str,
        help="Path to the repository where bundles are stored",
    )
    args = parser.parse_args()
    fp = FastApiAppPacker(args.repo_path, args.bundles_repo_path)
    fp.pack()


if __name__ == "__main__":
    main()

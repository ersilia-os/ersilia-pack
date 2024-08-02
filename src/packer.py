import os
import shutil
import argparse
import datetime
import uuid
import subprocess
import json
import yaml
import urllib.request
from .parsers import InstallParser, MetadataYml2JsonConverter

root = os.path.dirname(os.path.abspath(__file__))


class FastApiAppPacker(object):
    def __init__(self, repo_path, bundles_repo_path, conda_env_name=None):
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
        if not os.path.exists(os.path.join(self.bundle_dir, "installs")):
            os.makedirs(os.path.join(self.bundle_dir, "installs"))
        self.sh_file = os.path.join(self.bundle_dir, "installs", "install.sh")
        self.conda_env_name = conda_env_name

    def _get_model_id(self):
        json_file = os.path.join(self.dest_dir, "metadata.json")
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                data = json.load(f)
                return data["Identifier"]
        yml_file = os.path.join(self.dest_dir, "metadata.yml")
        if os.path.exists(yml_file):
            with open(yml_file, "r") as f:
                data = yaml.safe_load(f)
                return data["Identifier"]
        raise Exception("No metadata file found")

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
        print("Copying model")
        shutil.copytree(
            os.path.join(self.dest_dir, "model"), os.path.join(self.bundle_dir, "model")
        )
        print("Copying the favicon")

    def _load_metadata(self):
        json_file = os.path.join(self.dest_dir, "metadata.json")
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                data = json.load(f)
                return data
        yml_file = os.path.join(self.dest_dir, "metadata.yml")
        if os.path.exists(yml_file):
            data = MetadataYml2JsonConverter(yml_file).convert()
            return data
        raise Exception("No metadata file found")

    def _get_info(self):
        print("Getting info from metadata")
        data = self._load_metadata()
        info = {}
        info["Card"] = data
        info["model_id"] = data["Identifier"]
        info["Slug"] = data["Slug"]
        api_list = self._get_api_names_from_sh()
        if api_list is None:
            api_list = self._get_api_names_from_artifact()
        info["api_list"] = api_list
        with open(os.path.join(self.bundle_dir, "information.json"), "w") as f:
            json.dump(info, f, indent=4)
        self.info = info

    def _get_input_schema(self):
        print(self.info)
        input_entity = self.info["Card"]["Input"]
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
                lines = [l.rstrip("\n") for l in lines]
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

    def _convert_dockerfile_to_install_file(self):
        # TODO: This method should be improved to handle more complex Dockerfiles
        dockerfile_path = os.path.join(self.dest_dir, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            print("Dockerfile does not exist")
            return
        with open(dockerfile_path) as f:
            lines = f.readlines()
        install_lines = []
        for l in lines:
            if l.startswith("RUN"):
                install_lines += [l[4:]]
        with open(self.sh_file, "w") as f:
            f.write("\n".join(install_lines))

    def _has_install_yml(self):
        return os.path.exists(os.path.join(self.dest_dir, "install.yml"))
    
    def _has_dockerfile(self):
        return os.path.exists(os.path.join(self.dest_dir, "Dockerfile"))

    def _convert_install_yml_to_install_file(self):
        yml_path = os.path.join(self.dest_dir, "install.yml")
        if not os.path.exists(yml_path):
            print("Installs YAML does not exist")
            return
        if os.path.exists(self.sh_file):
            print("Install file already exists")
            return
        ymlparser = InstallParser(yml_path, conda_env_name=self.conda_env_name)
        ymlparser.write_bash_script(self.sh_file)

    def _install_packages(self):
        cmd = f"bash {self.sh_file}"
        subprocess.Popen(cmd, shell=True).wait()

    def pack(self):
        self._create_bundle_structure()
        self._get_favicon()
        self._create_app_files()
        self._edit_post_commands_app()
        self._get_info()
        self._get_input_schema()
        if self._has_install_yml():
            self._convert_install_yml_to_install_file()
        elif self._has_dockerfile():
            self._convert_dockerfile_to_install_file()
        else:
            print("No install file found. Proceeding anyway")
            pass
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
    parser.add_argument(
        "--conda_env_name",
        required=False,
        type=str,
        default=None,
        help="Name of the conda environment to use. This is optional",
    )
    args = parser.parse_args()
    fp = FastApiAppPacker(args.repo_path, args.bundles_repo_path, args.conda_env_name)
    fp.pack()


if __name__ == "__main__":
    main()

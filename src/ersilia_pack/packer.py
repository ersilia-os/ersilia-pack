import argparse
import datetime
import json
import os
import shutil
import subprocess
import urllib.request
import uuid

from .parsers import (
  DockerfileInstallParser,
  MetadataYml2JsonConverter,
  YAMLInstallParser,
)
from .utils import logger
from .templates.default import generic_example_output_file, FRAMEWORK_FOLDER  

root = os.path.dirname(os.path.abspath(__file__))


class FastApiAppPacker(object):
  def __init__(self, repo_path, bundles_repo_path, conda_env_name=None):
    self.root = os.path.dirname(os.path.abspath(__file__))
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
      logger.debug("Folder {0} existed. Removing it".format(self.bundle_dir))
      shutil.rmtree(self.bundle_dir)
    self.bundle_dir = os.path.join(self.bundle_dir, timestamp)
    os.makedirs(self.bundle_dir)
    if not os.path.exists(os.path.join(self.bundle_dir, "installs")):
      os.makedirs(os.path.join(self.bundle_dir, "installs"))
    self.sh_file = os.path.join(self.bundle_dir, "installs", "install.sh")
    if self._has_dockerfile():
      self.install_writer = DockerfileInstallParser(self.dest_dir, conda_env_name)
    elif self._has_install_yml():
      self.install_writer = YAMLInstallParser(self.dest_dir, conda_env_name)
    else:
      raise Exception("No install file found")  # TODO implement better exceptions

  def _get_model_id(self):
    data = self._load_metadata()
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
      logger.debug(f"File downloaded and saved to {file_path}")
    except Exception as e:
      logger.error(f"Failed to download file. Error: {e}")

  def _create_bundle_structure(self):
    logger.debug("Copying model")
    shutil.copytree(
      os.path.join(self.dest_dir, "model"),
      os.path.join(self.bundle_dir, "model"),
    )
    logger.debug("Copying the favicon")

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
    logger.debug("Getting info from metadata")
    data = self._load_metadata()
    info = {}
    info["card"] = data
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
    logger.debug(self.info)
    input_entity = self.info["card"]["Input"]
    if len(input_entity) > 1:
      return
    input_entity = input_entity[0].lower().replace(" ", "_")
    entity_path = os.path.join(self.bundle_dir, "app", "input_schemas", input_entity)
    input_shape = self.info["card"]["Input Shape"].lower().replace(" ", "_")
    schema_file = input_shape + ".py"

    if not os.path.exists(entity_path):
      os.makedirs(entity_path)

    shutil.copy(
      os.path.join(root, "templates", "input_schemas", input_entity, schema_file),
      os.path.join(entity_path, schema_file),
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
    app_dir = os.path.join(self.bundle_dir, "app")
    dirs = [
      app_dir,
      os.path.join(app_dir, "exceptions"),
      os.path.join(app_dir, "routers"),
      os.path.join(app_dir, "middleware"),
    ]
    for d in dirs:
      os.makedirs(d, exist_ok=True)

    shutil.copy(
      os.path.join(self.root, "templates", "app.py"), os.path.join(app_dir, "main.py")
    )
    open(os.path.join(app_dir, "__init__.py"), "w").close()

    files = [
      ("run_uvicorn.py", os.path.join(self.bundle_dir, "run_uvicorn.py")),
      ("utils.py", os.path.join(app_dir, "utils.py")),
      ("default.py", os.path.join(app_dir, "default.py")),
      ("exceptions/handlers.py", os.path.join(app_dir, "exceptions", "handlers.py")),
      ("exceptions/errors.py", os.path.join(app_dir, "exceptions", "errors.py")),
      ("middleware/rcontext.py", os.path.join(app_dir, "middleware", "rcontext.py")),
      ("middleware/__init__.py", os.path.join(app_dir, "middleware", "__init__.py")),
      ("routers/metadata.py", os.path.join(app_dir, "routers", "metadata.py")),
      ("routers/run.py", os.path.join(app_dir, "routers", "run.py")),
      ("routers/docs.py", os.path.join(app_dir, "routers", "docs.py")),
      ("routers/health.py", os.path.join(app_dir, "routers", "health.py")),
    ]

    templates_dir = os.path.join(self.root, "templates")
    for relative_path, dst in files:
      src = os.path.join(templates_dir, relative_path)
      shutil.copy(src, dst)

  def _edit_post_commands_app(self):
    api_names = self._get_api_names_from_sh()
    if len(api_names) > 0:
      with open(os.path.join(self.bundle_dir, "app", "main.py"), "r") as f:
        lines = f.readlines()
        lines = [l.rstrip("\n") for l in lines]
        lines += ["\n"]
        body_txt = "\n".join(lines)
        for api_name in api_names:
          with open(
            os.path.join(root, "templates", "post_code_chunks", "sh_files.txt"),
            "r",
          ) as g:
            txt = g.read()
            txt = txt.replace("$$$API_NAME$$$", api_name)
          txt += "\n"
          body_txt += txt
      with open(os.path.join(self.bundle_dir, "app", "main.py"), "w") as f:
        f.write(body_txt)
      return

  def _write_install_file(self):
    if not self.install_writer.check_file_exists():
      logger.warning(f"Install file {self.install_writer.file_type} does not exist")
      return
    if os.path.exists(self.sh_file):
      logger.debug("Install file already exists")
      return
    self.install_writer.write_bash_script(self.sh_file)

  def _has_install_yml(self):
    return os.path.exists(os.path.join(self.dest_dir, "install.yml"))

  def _has_dockerfile(self):
    return os.path.exists(os.path.join(self.dest_dir, "Dockerfile"))

  def _install_packages(self):
    cmd = f"bash {self.sh_file}"
    subprocess.Popen(cmd, shell=True).wait()

  def _get_example_output(self, path):
      with open(
        os.path.join(
          self.bundle_dir, "model", "framework", "examples", path
        ),
        "r",
      ) as f:
        example_output = f.readlines()[0]
      return example_output

  def _modify_python_exe(self):
    python_exe = self.install_writer.get_python_exe()
    with open(os.path.join(self.bundle_dir, "model", "framework", "run.sh"), "r") as f:
      lines = f.readlines()
    lines = [l.rstrip(os.linesep) for l in lines]
    for i, l in enumerate(lines):
      if l.startswith("python"):
        lines[i] = l.replace("python", python_exe)
    with open(os.path.join(self.bundle_dir, "model", "framework", "run.sh"), "w") as f:
      f.write(os.linesep.join(lines))

  def _write_api_schema(self):
    # This is a dropin method. It should be more sophisticated
    # This is to make ersilia CLI work with Dockerized models

    def resolve_output_meta_in_schema(output_type, output_shape):
      if len(output_type) == 1:
        output_type = output_type[0]
      elif (len(output_type) == 2) and (set(output_type) == set(["Integer", "Float"])):
        output_type = "Float"
      else:
        return

      if output_shape == "Single" and output_type == "Float":
        return "numeric"
      if output_shape == "Single" and output_type == "String":
        return "string"
      if output_shape == "Single" and output_type == "Integer":
        return "numeric"
      if output_shape == "List" and output_type == "Float":
        return "numeric_array"
      if output_shape == "List" and output_type == "String":
        return "string_array"

    with open(os.path.join(self.bundle_dir, "information.json"), "r") as f:
      metadata = json.load(f)

    if "card" in metadata:
      metadata = metadata["card"]
    output_type = resolve_output_meta_in_schema(
      metadata["Output Type"], metadata["Output Shape"]
    )
    api_names = self._get_api_names_from_sh()
    api_name = api_names[0] if isinstance(api_names, list) else api_names
    api_example_output_file = f"{api_name}_{generic_example_output_file}"
    print(api_example_output_file)
    if os.path.exists(os.path.join(self.bundle_dir, "model", "framework", "examples", api_example_output_file)):
        print("Path existed")
        example_output = self._get_example_output(api_example_output_file)
    else:
        example_output = self._get_example_output(generic_example_output_file)

    shape = len(example_output.split(","))
    meta = example_output.split(",")
    meta = [m.strip() for m in meta]
    input_schema = {
      "key": {"type": "string"},
      "input": {"type": "string"},
      "text": {"type": "string"},
    }
    output_schema = {
      "outcome": {
        "type": output_type,
        "shape": [shape],
        "meta": meta,
      }
    }
    api_schema = {"run": {"input": input_schema, "output": output_schema}}

    with open(os.path.join(self.bundle_dir, "api_schema.json"), "w") as f:
      json.dump(api_schema, f, indent=4)

  def _write_status_file(self):
    with open(os.path.join(self.bundle_dir, "status.json"), "w") as f:
      json.dump({"done": True}, f, indent=4)

  def pack(self):
    self._create_bundle_structure()
    self._get_favicon()
    self._create_app_files()
    # self._edit_post_commands_app()
    self._get_info()
    self._get_input_schema()
    self._write_install_file()
    self._install_packages()
    self._modify_python_exe()
    self._write_api_schema()
    self._write_status_file()


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

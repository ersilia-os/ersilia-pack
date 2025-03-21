import os

import yaml

from .install_parser import InstallParser

FILE_TYPE = "install.yml"


class YAMLInstallParser(InstallParser):
  def __init__(self, file_dir, conda_env_name=None):
    self.file_type = FILE_TYPE
    self.file_name = os.path.join(file_dir, self.file_type)
    self.data = self._load_yaml()
    super().__init__(self.file_name, conda_env_name)

  def _load_yaml(self):
    with open(self.file_name, "r") as file:
      return yaml.safe_load(file)

  def _get_python_version(self):
    if "python" not in self.data or not isinstance(self.data["python"], str):
      raise ValueError("Python version must be a string")
    return self.data["python"]

  def _get_commands(self):
    if "commands" not in self.data:
      raise KeyError("Missing 'commands' key in YAML file")
    return self.data["commands"]

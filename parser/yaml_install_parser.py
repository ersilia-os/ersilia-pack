import os
import yaml
from install_parser import InstallParser

class YAMLInstallParser(InstallParser):
    def __init__(self, file_dir, conda_env_name=None):
        self.file_type = "install.yml"
        file_name = os.path.join(file_dir, self.file_type)
        super().__init__(file_name, conda_env_name)

    def _get_python_version(self):
        with open(self.file_name, 'r') as file:
            self.data = yaml.safe_load(file)
        if not isinstance(self.data["python"], str):
            raise ValueError("Python version must be a string")
        return self.data["python"]

    def _get_commands(self):
        return self.data["commands"]

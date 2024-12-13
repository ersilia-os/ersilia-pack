import os
import re
import yaml
from .install_parser import InstallParser

class YAMLInstallParser(InstallParser):
    def __init__(self, file_dir, conda_env_name=None):
        self.file_type = "install.yml"
        self.file_name = os.path.join(file_dir, self.file_type)
        
        # Load YAML data before call
        self.data = self._load_yaml()
        
        # Call the super class constructor
        super().__init__(self.file_name, conda_env_name)

    def _load_yaml(self):
        with open(self.file_name, 'r') as file:
            return yaml.safe_load(file)

    def _get_python_version(self):
        if "python" not in self.data or not isinstance(self.data["python"], str):
            raise ValueError("Python version must be a string")
        return self.data["python"]

    def _get_commands(self):
        if "commands" not in self.data:
            raise KeyError("Missing 'commands' key in YAML file")
        
        commands = []
        for command in self.data["commands"]:
            if isinstance(command, dict) and command.get("tool") == "pip":
                commands.append(self._process_pip_command(command))
            else:
                # Handle other command types or formats if needed
                commands.append(command)
        return commands

    def _process_pip_command(self, command):
        """
        Reconstruct pip install command from YAML entry.

        Example input YAML format for pip commands:
        - tool: pip
          package: torchvision
          version: 0.17.1
          flags:
            --index-url: https://download.pytorch.org/whl/cpu
          url: git+https://github.com/pytorch/vision.git

        Output: 
        - "pip install torchvision==0.17.1 --index-url https://download.pytorch.org/whl/cpu"
        - "pip install git+https://github.com/pytorch/vision.git"
        """
        if "package" not in command and "url" not in command:
            raise ValueError("A pip command must specify either 'package' or 'url'")

        if "url" in command:
            url = command["url"]
            if not self._is_valid_url(url):
                raise ValueError(f"Invalid URL format: {url}")
            return f"pip install {url}"

        # If the command includes a package and version
        package = command["package"]
        version = command.get("version")
        flags = command.get("flags", [])

        pip_command = f"pip install {package}"
        if version:
            pip_command += f"=={version}"
        
        if flags:
            pip_command += " " + " ".join(flags)
        
        return pip_command

    def _is_valid_url(self, url):
        """
        Validate if the provided URL is a valid Git or HTTP URL.

        Accepts:
        - git+https://github.com/...
        - git+ssh://git@github.com/...
        - https://github.com/...
        - git+https://my.gitlab.com/repo.git
        """
        pattern = re.compile(r"^(git\+https://|git\+ssh://|https://).*")
        return bool(pattern.match(url))
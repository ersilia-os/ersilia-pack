import os
import re

import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../parser')))
from install_parser import InstallParser





class DockerfileInstallParser(InstallParser):
    def __init__(self, file_dir, conda_env_name=None):
        self.file_type = "Dockerfile"
        file_name = os.path.join(file_dir, self.file_type)
        super().__init__(file_name, conda_env_name)

    def _get_python_version(self):
        with open(self.file_name) as f:
            lines = f.readlines()
        for l in lines:
            if l.startswith("FROM"):
                m = re.search(r"python:(\d+\.\d+)", l)  # Updated regex to match "python:<version>"
                if m:
                    version = m.group(1)
                    return version  # Return the version directly
        raise ValueError("Python version not found in Dockerfile")


    @staticmethod
    def _process_pip_command(command):
        parts = command.split()
        if len(parts) < 3 or parts[0] != 'pip' or parts[1] != 'install':
            raise ValueError("Invalid format. Expected 'pip install package[==version]'")
        
        package_info = parts[2].split('==')
        if len(package_info) == 2:
            package, version = package_info
            return [parts[0], package, version]
        else:
            package = package_info[0]
            return [parts[0], package]

    @staticmethod
    def _process_conda_command(command):
        parts = command.split()
        if len(parts) < 3 or parts[0] != 'conda' or parts[1] != 'install':
            raise ValueError("Invalid format. Expected 'conda install [-c channel] package[==version|=version]'")
        
        if len(parts) == 3:
            package_info = re.split(r'==|=', parts[2])
            if len(package_info) == 2:
                package, version = package_info
                return ["conda", package, version, "default"]
            else:
                return ["conda", package_info[0], "default"]

        package_info = re.split(r'==|=', parts[4])
        if len(package_info) == 2:
            package, version = package_info
            return [parts[0], package, version, parts[3]]
        else:
            return [parts[0], package_info[0], parts[3]]

    def _get_commands(self):
        with open(self.file_name) as f:
            lines = f.readlines()
        commands = []
        for l in lines:
            if l.startswith("RUN"):
                l = l.strip("RUN").strip()
                if l.startswith("pip"):
                    commands.append(self._process_pip_command(l))
                elif l.startswith("conda"):
                    commands.append(self._process_conda_command(l))
                else:
                    commands.append(l)
        return commands

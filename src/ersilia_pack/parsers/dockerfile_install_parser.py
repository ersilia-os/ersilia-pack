import os
import re

from .install_parser import InstallParser

FILE_TYPE = "Dockerfile"


class DockerfileInstallParser(InstallParser):
  def __init__(self, file_dir, conda_env_name=None):
    self.file_type = FILE_TYPE
    file_name = os.path.join(file_dir, self.file_type)
    super().__init__(file_name, conda_env_name)

  def _get_python_version(self):
    """
    Extracts the Python version from the Dockerfile's FROM instruction.
    """
    with open(self.file_name, "r") as f:
      lines = f.readlines()
    for line in lines:
      if line.startswith("FROM"):
        match = re.search(r"py(\d+\.\d+|\d{2,3})", line)
        if match:
          version = match.group(1)
          if "." not in version:  # Convert py38 to 3.8
            version = f"{version[0]}.{version[1:]}"
          return version
    raise ValueError("Python version not found in Dockerfile")

  @staticmethod
  def _process_pip_command(command):
    """
    Processes a pip install command to extract the package name, version,
    and additional parameters like Git URLs, wheel file paths, or flags.

    Args:
        command (str): The pip install command.

    Returns:
        list: Parsed components of the pip command.

    Raises:
        ValueError: If the command is not valid or cannot be parsed.
    """
    parts = command.split()
    if len(parts) < 3 or parts[0] != "pip" or parts[1] != "install":
      raise ValueError("Invalid format. Expected 'pip install package[==version]'")

    package_info = parts[2].split("==")
    if len(package_info) == 2:
      package, version = package_info
      return [parts[0], package, version, *parts[3:]]
    else:
      package = package_info[0]
      return [parts[0], package, *parts[3:]]

  @staticmethod
  def _process_conda_command(command):
    """
    Processes a conda install command to extract the package name, version,
    and channel information.

    Args:
        command (str): The conda install command.

    Returns:
        list: Parsed components of the conda command.

    Raises:
        ValueError: If the command is not valid or cannot be parsed.
    """
    parts = command.split()
    if len(parts) < 3 or parts[0] != "conda" or parts[1] != "install":
      raise ValueError(
        "Invalid format. Expected 'conda install [-c channel] package[==version|=version]'"
      )

    # Handle the case where no channel is given
    if len(parts) == 3:
      package_info = re.split(
        r"==|=", parts[2]
      )  # Package version can be separated by == or =
      if len(package_info) == 2:
        package, version = package_info
        return ["conda", package, version, "default"]
      else:
        package = package_info[0]
        return ["conda", package, "default"]

    # Handle the case where a channel is given
    if len(parts) == 5:
      package_info = re.split(r"==|=", parts[4])
      if len(package_info) == 2:
        package, version = package_info
        return [parts[0], package, version, parts[3]]
      else:
        package = package_info[0]
        return [parts[0], package, parts[3]]
    if len(parts) == 7:
      if parts[2] == "-c" and parts[4] == "-c":
        package_info = re.split(r"==|=", parts[6])
        if len(package_info) == 2:
          package, version = package_info
          return [parts[0], package, version, parts[3], parts[5]]
        else:
          package = package_info[0]
          return [parts[0], package, parts[3], parts[5]]

  def _get_commands(self):
    """
    Parses RUN commands in the Dockerfile, identifying pip and conda commands.
    """
    with open(self.file_name, "r") as f:
      lines = f.readlines()

    commands = []
    for line in lines:
      if line.startswith("RUN"):
        command = line.strip("RUN").strip()
        if command.startswith("pip"):
          try:
            commands.append(self._process_pip_command(command))
          except ValueError as e:
            print(f"Skipping invalid pip command: {e}")
        elif command.startswith("conda"):
          try:
            commands.append(self._process_conda_command(command))
          except ValueError as e:
            print(f"Skipping invalid conda command: {e}")
        else:
          commands.append({"type": "other", "command": command})

    return commands

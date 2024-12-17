import re
import os
from src.ersilia_pack.parsers.install_parser import InstallParser


class DockerfileInstallParser(InstallParser):
    def __init__(self, file_dir, conda_env_name=None):
        self.file_type = "Dockerfile"
        file_name = os.path.join(file_dir, self.file_type)
        super().__init__(file_name, conda_env_name)

    def _get_python_version(self):
        """
        Extracts the Python version from the Dockerfile's FROM instruction.
        """
        with open(self.file_name, 'r') as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith("FROM"):
                match = re.search(r"py(\d+\.\d+|\d{2,3})", line)
                if match:
                    version = match.group(1)
                    if '.' not in version:  # Convert py38 to 3.8
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
        if len(parts) < 3 or parts[0] != 'pip' or parts[1] != 'install':
            raise ValueError("Invalid format. Expected 'pip install package[==version]'")

        package_parts = []
        flags = []
        for part in parts[2:]:
            if part.startswith('--'):
                flags.append(part)
            else:
                package_parts.append(part)

        if len(package_parts) == 1:
            package = package_parts[0]
            git_match = re.match(r'git\+([a-zA-Z0-9\-\.]+://[^\s]+)(@[\w\-\.]+)?', package)
            if git_match:
                git_url = git_match.group(1)
                git_tag = git_match.group(2)
                return ["pip", git_url, git_tag, None, flags]

            if package.endswith('.whl') or re.match(r'https?://.*\.whl$', package):
                return ["pip", package, None, None, flags]

            package_match = re.match(
                r'([a-zA-Z0-9_\-\.]+)(\[.*\])?(==|>=|<=|~=|!=)?([\d\.]*)', package
            )
            if package_match:
                package_name = package_match.group(1)
                extras = package_match.group(2)
                version_operator = package_match.group(3)
                version = package_match.group(4)
                # Separate the version operator from the version
                version = version if version else None
                return ["pip", package_name, version, extras, flags]

        raise ValueError(f"Unable to parse pip command: '{command}'.")

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
        if len(parts) < 3 or parts[0] != 'conda' or parts[1] != 'install':
            raise ValueError(f"Invalid conda command: '{command}'.")

        channel = "default"
        package_info = None

        if '-c' in parts:
            channel_index = parts.index('-c') + 1
            if channel_index < len(parts):
                channel = parts[channel_index]
                package_info = parts[channel_index + 1] if len(parts) > channel_index + 1 else None
        else:
            package_info = parts[2]

        if package_info:
            package_parts = re.split(r'==|=', package_info)
            package = package_parts[0]
            version = package_parts[1] if len(package_parts) > 1 else "default"
            return ["conda", package, version, channel]

        raise ValueError(f"Unable to parse conda command: '{command}'.")

    def _get_commands(self):
        """
        Parses RUN commands in the Dockerfile, identifying pip and conda commands.
        """
        with open(self.file_name, 'r') as f:
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

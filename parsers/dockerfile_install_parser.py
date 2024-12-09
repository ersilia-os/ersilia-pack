import re
from .install_parser import InstallParser



class DockerfileInstallParser(InstallParser):
    def __init__(self, file_path, conda_env_name=None):
        self.file_name = file_path
        super().__init__(self.file_name, conda_env_name)
    
    def _get_python_version(self):
        with open(self.file_name, 'r') as f:
            lines = f.readlines()
        for l in lines:
            print(l)
            if l.startswith("FROM"):
                m = re.search(r"py(\d{2,3})", l)
                if m:
                   # version = m.group(1).strip('py')
                    version = f"{m.group(1)[0]}.{m.group(1)[1:]}"
                    return version
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
        
        # Handle the case where no channel is given
        if len(parts) == 3:
            package_info = re.split(r'==|=', parts[2]) # Package version can be separated by == or =
            if len(package_info) == 2:
                package, version = package_info
                return ["conda", package, version, "default"]
            else:
                package = package_info[0]
                return ["conda", package, "default"]
        
        # Handle the case where a channel is given
        package_info = re.split(r'==|=', parts[4])
        if len(package_info) == 2:
            package, version = package_info
            return [parts[0], package, version, parts[3]]
        else:
            package = package_info[0]
            return [parts[0], package, parts[3]]

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

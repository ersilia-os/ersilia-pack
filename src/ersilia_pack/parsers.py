# TODO Refactor this file to make a sub-package instead of having each class in a single file
import re
import yaml
import os
import collections
import json
import textwrap

class InstallParser:
    def __init__(self, file_name, conda_env_name=None):
        self.conda_env_name = conda_env_name
        self.file_name = file_name
        self.python_version = self._get_python_version()

    def _get_python_version(self):
        raise NotImplementedError("Implement this in subclass")
    
    def _get_commands(self):
        raise NotImplementedError("Implement this in subclass")
    
    @staticmethod
    def _eval_conda_prefix():
        # This returns an empty string if conda is not discoverable
        return os.popen("conda info --base").read().strip()
    
    def get_python_exe(self):
        conda_prefix = self._eval_conda_prefix()
        if not conda_prefix:
            return "python"
        if self.conda_env_name is None:
            return f"{conda_prefix}/bin/python"
        return f"{conda_prefix}/envs/{self.conda_env_name}/bin/python"

    @staticmethod
    def _has_conda(commands):
        for command in commands:
            if type(command) is list and command[0] == "conda":
                return True
        return False
    
    def _convert_commands_to_bash_script(self):
        lines = []
        commands = self._get_commands()
        has_conda = self._has_conda(commands)
        conda_prefix = self._eval_conda_prefix()
        python_exe = self.get_python_exe()
        for command in commands:
            if type(command) is list:
                if command[0] == "pip":
                    assert len(command) == 3, "pip command must have 3 arguments"
                    cmd = f"{python_exe} -m pip install " + command[1] + "==" + command[2]
                elif command[0] == "conda":
                    assert len(command) == 4, "conda command must have 4 arguments"
                    if command[3] == "default":
                        cmd = "conda install " + command[1] + "=" + command[2]
                    else:
                        cmd = "conda install -c " + command[3] + " " + command[1] + "=" + command[2]
                    cmd += " -y"
                else:
                    raise ValueError("Unknown command type specified as a list")
            else:
                cmd = command
            lines += [cmd]
        txt = ""
        if has_conda:
            if self.conda_env_name is None:
                conda_env_name = "base"
                self.python_exe = "python_exe=$conda_prefix/bin/python"
            else:
                conda_env_name = self.conda_env_name
                self.python_exe = f"python_exe=$conda_prefix/envs/{conda_env_name}/bin/python"
            conda_lines = [
                f"source {conda_prefix}/etc/profile.d/conda.sh",
                "conda activate " + conda_env_name
            ]
            lines = [self.python_exe] + conda_lines + lines
            
            txt = textwrap.dedent(txt) + os.linesep
        txt += os.linesep.join(lines)
        return txt
    
    def write_bash_script(self, file_name=None):
        if file_name is None:
            file_name = self.file_name.split(".")[0] + ".sh"
        with open(file_name, 'w') as file:
            file.write(self._convert_commands_to_bash_script())

    def check_file_exists(self):
        return os.path.exists(self.file_name)
    

class YAMLInstallParser(InstallParser):
    def __init__(self, file_dir, conda_env_name=None):
        self.file_type = "install.yml"
        file_name = os.path.join(file_dir, self.file_type)
        super().__init__(file_name, conda_env_name)
    
    def _get_python_version(self):
        with open(self.file_name, 'r') as file:
            self.data = yaml.safe_load(file)
        if type(self.data["python"]) != str:
            raise ValueError("Python version must be a string")
        return self.data["python"]
    
    @staticmethod
    def _validate_pip_command(command):
        if len(command) < 3 or command[0] != 'pip':
            raise ValueError("Invalid pip command format. Must start with 'pip' and include a package.")
    
        if command[1] == "git":
            if len(command) != 4:
                raise ValueError("Invalid VCS pip command. Must specify 'git', URL, and commit SHA.")
            return command
        elif '--index-url' in command:
            if len(command) < 5:
                raise ValueError("Invalid pip command with --index-url. Must include package, version, and URL.")
            return command
        elif len(command) == 3:
            return command
        else:
            raise ValueError("Invalid pip command. Must include package and version or URL.")


    def _get_commands(self):
        commands = self.data["commands"]
        validated_commands = []
        for command in commands:
            if command[0] == 'pip':
                validated_commands.append(self._validate_pip_command(command))
            else:
                validated_commands.append(command)
        return validated_commands

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
                m = re.search(r"py(\d+)", l)
                if m:
                    version = m.group(1).strip('py')
                    version = version[0] + "." + version[1:]
                    return version
        raise ValueError("Python version not found in Dockerfile")

    @staticmethod
    def _process_pip_command(self, command):
        parts = command.split()
        if len(parts) < 3 or parts[0] != 'pip' or parts[1] != 'install':
            raise ValueError("Invalid format. Expected 'pip install package[==version]'")
        
        if parts[2].startswith("git+"):
            return ['pip', 'git', parts[2], parts[2].split('@')[-1]]
        elif '--index-url' in parts:
            idx = parts.index('--index-url')
            return [parts[0], parts[2], parts[idx:]]
        elif "==" in parts[2]:
            package, version = parts[2].split("==")
            return [parts[0], package, version]
        else:
            raise ValueError("Invalid format. Specify the version or use VCS/URL.")
    
    @staticmethod
    def _process_conda_command(self, command):
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

class MetadataYml2JsonConverter:

    def __init__(self, yml_file, json_file=None):
        self.yml_file = yml_file
        with open(self.yml_file, 'r') as f:
            self.data = yaml.safe_load(f)
        self.json_file = json_file

    def _tolist(self, value):
        if type(value) is str:
            return [value]
        else:
            return value
        
    def _tostr(self, value):
        if type(value) is list:
            if len(value) == 1:
                return value[0]
            else:
                raise Exception("Value is a list with more than one element")
        else:
            return value

    def convert(self):
        data = collections.OrderedDict()
        data["Identifier"] = self._tostr(self.data["Identifier"])
        data["Slug"] = self._tostr(self.data["Slug"])
        if "Status" in self.data:
            data["Status"] = self._tostr(self.data["Status"])
        data["Title"] = self._tostr(self.data["Title"])
        data["Description"] = self._tostr(self.data["Description"])
        data["Mode"] = self._tostr(self.data["Mode"])
        data["Input"] = self._tolist(self.data["Input"])
        data["Input Shape"] = self._tostr(self.data["Input Shape"])
        data["Task"] = self._tolist(self.data["Task"])
        data["Output"] = self._tolist(self.data["Output"])
        data["Output Type"] = self._tolist(self.data["Output Type"])
        data["Output Shape"] = self._tostr(self.data["Output Shape"])
        data["Interpretation"] = self._tostr(self.data["Interpretation"])
        data["Tag"] = self._tolist(self.data["Tag"])
        data["Publication"] = self._tostr(self.data["Publication"])
        data["Source Code"] = self._tostr(self.data["Source Code"])
        data["License"] = self._tostr(self.data["License"])
        if "Contributor" in self.data:
            data["Contributor"] = self._tostr(self.data["Contributor"])
        if "S3" in self.data:
            data["S3"] = self._tostr(self.data["S3"])
        if "DockerHub" in self.data:
            data["DockerHub"] = self._tostr(self.data["DockerHub"])
        if "Docker Architecture" in self.data:
            data["Docker Architecture"] = self._tolist(self.data["Docker Architecture"])
        if self.json_file is None:
            return data
        with open(self.json_file, 'w') as f:
            f.write(json.dumps(data, indent=4))

if __name__ == "__main__":
    parser = DockerfileInstallParser("<path here>")
    parser.write_bash_script()
    #converter = MetadataYml2JsonConverter("metadata.yml", "metadata.json")
    #converter.convert()

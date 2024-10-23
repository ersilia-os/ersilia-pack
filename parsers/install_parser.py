import os
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
            if isinstance(command, list) and command[0] == "conda":
                return True
        return False

    def _convert_commands_to_bash_script(self):
        lines = []
        commands = self._get_commands()
        has_conda = self._has_conda(commands)
        conda_prefix = self._eval_conda_prefix()
        python_exe = self.get_python_exe()
        for command in commands:
            if isinstance(command, list):
                if command[0] == "pip":
                    assert len(command) == 3, "pip command must have 3 arguments"
                    cmd = f"{python_exe} -m pip install {command[1]}=={command[2]}"
                elif command[0] == "conda":
                    assert len(command) == 4, "conda command must have 4 arguments"
                    if command[3] == "default":
                        cmd = f"conda install {command[1]}={command[2]}"
                    else:
                        cmd = f"conda install -c {command[3]} {command[1]}={command[2]}"
                    cmd += " -y"
                else:
                    raise ValueError("Unknown command type specified as a list")
            else:
                cmd = command
            lines.append(cmd)

        txt = ""
        if has_conda:
            conda_env_name = self.conda_env_name if self.conda_env_name else "base"
            self.python_exe = f"python_exe=$conda_prefix/envs/{conda_env_name}/bin/python" if self.conda_env_name else "python_exe=$conda_prefix/bin/python"
            conda_lines = [
                f"source {conda_prefix}/etc/profile.d/conda.sh",
                f"conda activate {conda_env_name}"
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

import yaml
import os
import collections
import json
import textwrap


class InstallParser(object):
    def __init__(self, file_name, conda_env_name=None):
        self.conda_env_name = conda_env_name
        self.file_name = file_name
        with open(self.file_name, 'r') as file:
            self.data = yaml.safe_load(file)
        if type(self.data["python"]) != str:
            raise ValueError("Python version must be a string")

    def _get_python_version(self):
        return self.data["python"]
    
    def _get_commands(self):
        # TODO make it more sophisticate for multiple platforms or command types
        return self.data["commands"]
        
    def _convert_commands_to_bash_script(self):
        lines = []
        has_conda = False
        for command in self._get_commands():
            if type(command) is list:
                if command[0] == "pip":
                    assert len(command) == 3, "pip command must have 3 arguments"
                    cmd = "pip install " + command[1] + "==" + command[2]
                elif command[0] == "conda":
                    assert len(command) == 4, "conda command must have 4 arguments"
                    has_conda = True
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
            else:
                conda_env_name = self.conda_env_name
            conda_lines = [
                "source $conda_prefix/etc/profile.d/conda.sh",
                "conda activate " + conda_env_name
            ]
            lines = conda_lines + lines
            txt = '''
                current_env=$(conda info --envs | grep '*' | awk '{print $1}')
                if [ -z "$current_env" ]; then
                    current_env="base"
                    conda activate base
                fi
                if [ "$current_env" == "base" ]; then
                    conda_prefix=$CONDA_PREFIX
                else
                    conda_prefix=$CONDA_PREFIX_1
                fi
                '''
            txt = textwrap.dedent(txt) + os.linesep
        txt += os.linesep.join(lines)
        return txt
    
    def write_bash_script(self, file_name=None):
        if file_name is None:
            file_name = self.file_name.split(".")[0] + ".sh"
        with open(file_name, 'w') as file:
            file.write(self._convert_commands_to_bash_script())


class MetadataYml2JsonConverter(object):

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
    parser = InstallParser("/Users/mduranfrigola/Documents/GitHub/eos-template-2/install.yml")
    parser.write_bash_script()
    #converter = MetadataYml2JsonConverter("metadata.yml", "metadata.json")
    #converter.convert()

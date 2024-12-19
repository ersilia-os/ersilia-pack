import json
import collections
import yaml

class MetadataYml2JsonConverter:
    def __init__(self, yml_file, json_file=None):
        self.yml_file = yml_file
        with open(self.yml_file, 'r') as f:
            self.data = yaml.safe_load(f)
        self.json_file = json_file

    def _tolist(self, value):
        return [value] if isinstance(value, str) else value

    def _tostr(self, value):
        if isinstance(value, list):
            if len(value) == 1:
                return value[0]
            else:
                raise Exception("Value is a list with more than one element")
        return value

    def convert(self):
        data = collections.OrderedDict()
        
        # Use .get() to handle missing keys
        data["Identifier"] = self._tostr(self.data.get("Identifier", "default_id"))
        data["Slug"] = self._tostr(self.data.get("Slug", "default_slug"))
        data["Status"] = self._tostr(self.data.get("Status", "default_status"))
        data["Title"] = self._tostr(self.data.get("Title", "default_title"))
        data["Description"] = self._tostr(self.data.get("Description", "default_description"))
        data["Mode"] = self._tostr(self.data.get("Mode", "default_mode"))
        data["Input"] = self._tolist(self.data.get("Input", []))
        data["Input Shape"] = self._tostr(self.data.get("Input Shape", "default_shape"))
        data["Task"] = self._tolist(self.data.get("Task", []))
        data["Output"] = self._tolist(self.data.get("Output", []))
        data["Output Type"] = self._tolist(self.data.get("Output Type", []))
        data["Output Shape"] = self._tostr(self.data.get("Output Shape", "default_output_shape"))
        data["Interpretation"] = self._tostr(self.data.get("Interpretation", "default_interpretation"))
        data["Framework"] = self._tostr(self.data.get("Framework", "default_framework"))
        data["Code"] = self._tostr(self.data.get("Code", "default_code"))
        data["License"] = self._tostr(self.data.get("License", "default_license"))
        data["Email"] = self._tostr(self.data.get("Email", "default_email"))
        data["Version"] = self._tostr(self.data.get("Version", "default_version"))
        data["Tags"] = self._tolist(self.data.get("Tags", []))

        if self.json_file is None:
            self.json_file = self.yml_file.replace(".yml", ".json")
        
        with open(self.json_file, 'w') as f:
            json.dump(data, f, indent=4)

        return data
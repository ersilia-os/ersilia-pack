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
        data["Framework"] = self._tostr(self.data["Framework"])
        data["Code"] = self._tostr(self.data["Code"])
        data["License"] = self._tostr(self.data["License"])
        data["Email"] = self._tostr(self.data["Email"])
        data["Version"] = self._tostr(self.data["Version"])
        data["Tags"] = self._tolist(self.data["Tags"])

        if self.json_file is None:
            self.json_file = self.yml_file.replace(".yml", ".json")
        with open(self.json_file, 'w') as f:
            json.dump(data, f, indent=4)

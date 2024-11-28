import yaml
import json
import collections

class MetadataYml2JsonConverter:
    def __init__(self, yml_file, json_file=None):
        self.yml_file = yml_file
        with open(self.yml_file, 'r') as f:
            self.data = yaml.safe_load(f)
        self.json_file = json_file

    def _tolist(self, value):
        if isinstance(value, str):
            return [value]
        return value
        
    def _tostr(self, value):
        if isinstance(value, list):
            if len(value) == 1:
                return value[0]
            raise Exception("Value is a list with more than one element")
        return value

    def convert(self):
        data = collections.OrderedDict()
        required_fields = [
            "Identifier", "Slug", "Title", "Description", "Mode",
            "Input", "Input Shape", "Task", "Output", "Output Type",
            "Output Shape", "Interpretation", "Tag", "Publication",
            "Source Code", "License"
        ]
        
        optional_fields = [
            "Status", "Contributor", "S3", "DockerHub", "Docker Architecture"
        ]

        for field in required_fields:
            if field in ["Input", "Task", "Output", "Output Type", "Tag"]:
                data[field] = self._tolist(self.data[field])
            else:
                data[field] = self._tostr(self.data[field])

        for field in optional_fields:
            if field in self.data:
                if field == "Docker Architecture":
                    data[field] = self._tolist(self.data[field])
                else:
                    data[field] = self._tostr(self.data[field])

        if self.json_file is None:
            return data
            
        with open(self.json_file, 'w') as f:
            json.dump(data, f, indent=4)
import collections
import json

import yaml


class MetadataYml2JsonConverter:
  def __init__(self, yml_file, json_file=None):
    self.yml_file = yml_file
    with open(self.yml_file, "r") as f:
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
    with open(self.json_file, "w") as f:
      json.dump(data, f, indent=4)

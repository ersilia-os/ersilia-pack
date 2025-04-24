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
  
  def _tofloat(self, value):
    if isinstance(value, str):
      try:
        return float(value)
      except ValueError:
        raise Exception("Value is not a float")
    return float(value)
  
  def _toint(self, value):
    if isinstance(value, str):
      try:
        return int(value)
      except ValueError:
        raise Exception("Value is not an int")
    return int(value)

  def convert(self):
    data = collections.OrderedDict()
    if "Identifier" in self.data:
      data["Identifier"] = self._tostr(self.data["Identifier"])
    if "Slug" in self.data:
      data["Slug"] = self._tostr(self.data["Slug"])
    if "Status" in self.data:
      data["Status"] = self._tostr(self.data["Status"])
    if "Title" in self.data:
      data["Title"] = self._tostr(self.data["Title"])
    if "Description" in self.data:
      data["Description"] = self._tostr(self.data["Description"])
    if "Deployment" in self.data:
      data["Deployment"] = self._tolist(self.data["Deployment"])
    if "Source" in self.data:
      data["Source"] = self._tostr(self.data["Source"])
    if "Source Type" in self.data:
      data["Source Type"] = self._tostr(self.data["Source Type"])
    if "Task" in self.data:
      data["Task"] = self._tostr(self.data["Task"])
    if "Subtask" in self.data:
      data["Subtask"] = self._tostr(self.data["Subtask"])
    if "Input" in self.data:
      data["Input"] = self._tolist(self.data["Input"])
    if "Input Dimension" in self.data:
      data["Input Dimension"] = self._toint(self.data["Input Dimension"])
    if "Output" in self.data:
      data["Output"] = self._tolist(self.data["Output"])
    if "Output Dimension" in self.data:
      data["Output Dimension"] = self._toint(self.data["Output Dimension"])
    if "Output Consistency" in self.data:
      data["Output Consistency"] = self._tostr(self.data["Output Consistency"])
    if "Interpretation" in self.data:
      data["Interpretation"] = self._tostr(self.data["Interpretation"])
    if "Tag" in self.data:
      data["Tag"] = self._tolist(self.data["Tag"])
    if "Biomedical Area" in self.data:
      data["Biomedical Area"] = self._tolist(self.data["Biomedical Area"])
    if "Target Organism" in self.data:
      data["Target Organism"] = self._tolist(self.data["Target Organism"])
    if "Publication Type" in self.data:
      data["Publication Type"] = self._tostr(self.data["Publication Type"])
    if "Publication Year" in self.data:
      data["Publication Year"] = self._toint(self.data["Publication Year"])
    if "Publication" in self.data:
      data["Publication"] = self._tostr(self.data["Publication"])
    if "Source Code" in self.data:
      data["Source Code"] = self._tostr(self.data["Source Code"])
    if "License" in self.data:
      data["License"] = self._tostr(self.data["License"])
    if "Contributor" in self.data:
      data["Contributor"] = self._tostr(self.data["Contributor"])
    if "Incorporation Date" in self.data:
      data["Incorporation Date"] = self._tostr(self.data["Incorporation Date"])
    if "S3" in self.data:
      data["S3"] = self._tostr(self.data["S3"])
    if "DockerHub" in self.data:
      data["DockerHub"] = self._tostr(self.data["DockerHub"])
    if "Docker Architecture" in self.data:
      data["Docker Architecture"] = self._tolist(self.data["Docker Architecture"])
    if "Docker Pack Method" in self.data:
      data["Docker Pack Method"] = self._tostr(self.data["Docker Pack Method"])
    if "Model Size" in self.data:
      data["Model Size"] = self._tofloat(self.data["Model Size"])
    if "Environment Size" in self.data:
      data["Environment Size"] = self._tofloat(self.data["Environment Size"])
    if "Image Size" in self.data:
      data["Image Size"] = self._tofloat(self.data["Image Size"])
    if "Computational Performance 4" in self.data:
      data["Computational Performance 4"] = self._tofloat(self.data["Computational Performance 4"])
    if "Computational Performance 7" in self.data:
      data["Computational Performance 7"] = self._tofloat(self.data["Computational Performance 7"])
    if "Computational Performance 12" in self.data:
      data["Computational Performance 12"] = self._tofloat(self.data["Computational Performance 12"])
    if "Computational Performance 20" in self.data:
      data["Computational Performance 20"] = self._tofloat(self.data["Computational Performance 20"])
    if "Computational Performance 34" in self.data:
      data["Computational Performance 34"] = self._tofloat(self.data["Computational Performance 34"])
    if "Computational Performance 58" in self.data:
      data["Computational Performance 58"] = self._tofloat(self.data["Computational Performance 58"])
    if "Computational Performance 100" in self.data:
      data["Computational Performance 100"] = self._tofloat(self.data["Computational Performance 100"])
    if self.json_file is None:
      return data
    with open(self.json_file, "w") as f:
      json.dump(data, f, indent=4)
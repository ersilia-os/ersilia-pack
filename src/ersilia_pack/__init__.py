import json
import os
import yaml


class BasePacker(object):
    def __init__(self, repo_path, bundles_repo_path):
        self.dest_dir = repo_path
        self.bundles_repo_path = bundles_repo_path
        if not os.path.exists(self.dest_dir):
            raise Exception("Model path {0} does not exist".format(self.dest_dir))
        self.model_id = self.get_model_id()

    def get_model_id(self):
        json_file = os.path.join(self.dest_dir, "metadata.json")
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                data = json.load(f)
                return data["Identifier"]
        yml_file = os.path.join(self.dest_dir, "metadata.yml")
        if os.path.exists(yml_file):
            with open(yml_file, "r") as f:
                data = yaml.safe_load(f)
                return data["Identifier"]
        raise Exception("No metadata file found")
    
    def get_api_names(self):
        api_names = []
        for fn in os.listdir(os.path.join(self.dest_dir, "model", "framework")):
            if fn.endswith(".sh"):
                api_names += [fn.split(".sh")[0]]
        return api_names
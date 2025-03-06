import argparse
import os

from . import BasePacker
from .utils import logger


class SimpleModelLinter(BasePacker):
  def __init__(self, repo_path):
    BasePacker.__init__(self, repo_path=repo_path, bundles_repo_path=None)

  def _check_model_id(self):
    if not self.model_id.startswith("eos") or len(self.model_id) != 7:
      raise Exception("Model identifier is not correct")

  def _check_metadata(self):
    if os.path.exists(os.path.join(self.dest_dir, "metadata.yml")):
      return
    if os.path.exists(os.path.join(self.dest_dir, "metadata.json")):
      return
    raise Exception("No metadata file found")

  def _check_installs(self):
    if os.path.exists(os.path.join(self.dest_dir, "install.yml")):
      return
    if os.path.exists(os.path.join(self.dest_dir, "Dockerfile")):
      return
    raise Exception("No install file found")

  def _check_license(self):
    if os.path.exists(os.path.join(self.dest_dir, "LICENSE")):
      return
    raise Exception("No LICENSE file found")

  def _check_readme(self):
    if os.path.exists(os.path.join(self.dest_dir, "README.md")):
      return
    raise Exception("No README file found")

  def _check_model_folder(self):
    if os.path.exists(os.path.join(self.dest_dir, "model", "framework")):
      return
    raise Exception("No model folder found")

  def _check_apis(self):
    api_names = self.get_api_names()
    if len(api_names) == 0:
      raise Exception("No API names found. An API should be a .sh file")

  def _check_examples(self):
    api_names = self.get_api_names()
    for api_name in api_names:
      if not os.path.exists(
        os.path.join(
          self.dest_dir, "model", "framework", "examples", f"{api_name}_input.csv"
        )
      ):
        raise Exception("Example input not found for {0}".format(api_name))
      if not os.path.exists(
        os.path.join(
          self.dest_dir, "model", "framework", "examples", f"{api_name}_output.csv"
        )
      ):
        raise Exception("Example output not found for {0}".format(api_name))

  def check(self):
    self._check_model_id()
    self._check_metadata()
    self._check_installs()
    self._check_license()
    self._check_readme()
    self._check_model_folder()
    self._check_examples()
    logger.info("Model {0} seems to be valid".format(self.model_id))


def main():
  parser = argparse.ArgumentParser(description="ErsiliaAPI app")
  parser.add_argument(
    "--repo_path", required=True, type=str, help="Path to the model repository"
  )
  args = parser.parse_args()
  sml = SimpleModelLinter(args.repo_path)
  sml.check()

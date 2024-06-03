from fastapi import FastAPI
import uuid
import json
import csv
import os
import tempfile
import subprocess
from typing import List, Union, Dict
from pydantic import RootModel


root = os.path.dirname(os.path.abspath(__file__))
bundle_folder = os.path.abspath(os.path.join(root, ".."))
framework_folder = os.path.abspath(os.path.join(root, "..", "model", "framework"))
tmp_folder = tempfile.mkdtemp(prefix="ersilia-")


with open(os.path.join(bundle_folder, "info.json"), "r") as f:
    info_data = json.load(f)


app = FastAPI(
    title="{0}:{1}".format(info_data["card"]["Identifier"], info_data["card"]["Slug"]),
    description=info_data["card"]["Description"],
    version="latest",
)

# Read root

@app.get("/", tags=["Checks"])
def read_root():
    return {info_data["card"]["Identifier"]: info_data["card"]["Slug"]}


# Metadata

@app.get("/card", tags=["Metadata"])
def card():
    """
    Get card information

    """
    return info_data["card"]


@app.get("/model_id", tags=["Metadata"])
def model_id():
    """
    Get model identifier

    """
    return info_data["card"]["Identifier"]


@app.get("/slug", tags=["Metadata"])
def slug():
    """
    Get the slug

    """
    return info_data["card"]["Slug"]


@app.get("/input_type", tags=["Metadata"])
def input_type():
    """
    Get the input type

    """
    return info_data["card"]["input_type"]


@app.get("/example_input", tags=["Metadata"])
def example_input():
    """
    Get a predefined input example

    """
    input_list = []
    with open(os.path.join(framework_folder, "example_input.csv"), "r") as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            input_list += r
    return input_list


@app.get("/example_output", tags=["Metadata"])
def example_output():
    """
    Get a precalculated example output

    """
    output_list = []
    with open(os.path.join(framework_folder, "example_output.csv"), "r") as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            output_list += [r]
    return output_list


@app.get("/output_header", tags=["Metadata"])
def output_header():
    """
    Get the header of the output

    """
    with open(os.path.join(framework_folder, "example_output.csv"), "r") as f:
        reader = csv.reader(f)
        return next(reader)


# Model endpoints

# Define the expected request body using Pydantic
class StringList(RootModel[List[str]]):
    pass

class DictList(RootModel[List[Dict[str, str]]]):
    pass

InputList = Union[StringList, DictList]


@app.post("/run", tags=["App"])
async def run(request: InputList = None):
    """
    Pass a list of inputs to the model. The model will return a list of outputs

    """
    data = request.root
    # This is for compatibility with previous eos-templates (based on bentoml)
    d0 = data[0]
    if isinstance(d0, Dict):
        if "input" in d0.keys():
            data = [d["input"] for d in data]

    tag = str(uuid.uuid4())
    input_file = "{0}/{1}".format(tmp_folder, "input-{0}.csv".format(tag))
    with open(input_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["input"])
        for r in data:
            writer.writerow([r])
    output_file = "{0}/{1}".format(tmp_folder, "output-{0}.csv".format(tag))
    cmd = "bash {0}/run.sh {0} {1} {2}".format(
        framework_folder, input_file, output_file, root
    )
    print(cmd)
    subprocess.Popen(cmd, shell=True).wait()
    R = []
    with open(output_file, "r") as f:
        reader = csv.reader(f)
        for r in reader:
            R += [r]
    os.remove(input_file)
    os.remove(output_file)
    return R
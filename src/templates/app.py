from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import FileResponse
import uuid
import json
import csv
import os
import tempfile
import subprocess
import sys
from enum import Enum


root = os.path.dirname(os.path.abspath(__file__))
bundle_folder = os.path.abspath(os.path.join(root, ".."))
framework_folder = os.path.abspath(os.path.join(root, "..", "model", "framework"))
tmp_folder = tempfile.mkdtemp(prefix="ersilia-")
static_dir = os.path.join(bundle_folder, "static")

sys.path.insert(0, root)
from input_schema import InputSchema, exemplary_input
from utils import orient_to_json


with open(os.path.join(bundle_folder, "info.json"), "r") as f:
    info_data = json.load(f)


app = FastAPI(
    title="{0}:{1}".format(info_data["card"]["Identifier"], info_data["card"]["Slug"]),
    description=info_data["card"]["Description"],
    version="latest",
)


# Output formats (orientations)

class OrientEnum(str, Enum):
    records = "records"
    columns = "columns"
    values = "values"
    split = "split"
    index = "index"


# Root

@app.get("/", tags=["Root"])
def read_root():
    return {info_data["card"]["Identifier"]: info_data["card"]["Slug"]}


# Serve the favicon
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Get the Ersilia favicon."""
    return FileResponse(os.path.join(static_dir, "favicon.ico"))


# Metadata

@app.get("/card", tags=["Metadata"])
def card():
    """
    Get card information

    """
    return info_data["card"]


@app.get("/card/model_id", tags=["Metadata"])
def model_id():
    """
    Get model identifier

    """
    return info_data["card"]["Identifier"]


@app.get("/card/slug", tags=["Metadata"])
def slug():
    """
    Get the slug

    """
    return info_data["card"]["Slug"]


@app.get("/card/input_type", tags=["Metadata"])
def input_entity():
    """
    Get the input type

    """
    return info_data["card"]["Input"]


@app.get("/card/input_shape", tags=["Metadata"])
def input_shape():
    """
    Get the input shape

    """
    return info_data["card"]["Input Shape"]


@app.get("/example/input", tags=["Metadata"])
def example_input():
    """
    Get a predefined input example

    """
    input_list = []
    with open(os.path.join(framework_folder, "example.csv"), "r") as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            input_list += r
    return input_list


@app.get("/example/output", tags=["Metadata"])
def example_output(orient: OrientEnum = Query(OrientEnum.records)):
    """
    Get a precalculated example output

    """
    output_list = []
    with open(os.path.join(framework_folder, "output.csv"), "r") as f:
        reader = csv.reader(f)
        columns = next(reader)
        for r in reader:
            output_list += [r]

    with open(os.path.join(framework_folder, "example.csv"), "r") as f:
        reader = csv.reader(f)
        next(reader)
        index = []
        for r in reader:
            index += [r[0]]

    response = orient_to_json(output_list, columns, index, orient)
    return response


@app.get("/columns/input", tags=["Metadata"])
def columns_input():
    """
    Get the header of the input

    """
    with open(os.path.join(framework_folder, "example.csv"), "r") as f:
        reader = csv.reader(f)
        return next(reader)


@app.get("/columns/output", tags=["Metadata"])
def columns_output():
    """
    Get the header of the output

    """
    with open(os.path.join(framework_folder, "example_output.csv"), "r") as f:
        reader = csv.reader(f)
        return next(reader)


@app.post("/run", tags=["App"])
async def run(request: InputSchema = Body(..., example=exemplary_input), orient: OrientEnum = Query(OrientEnum.records)):
    """
    Make a request to the model.

    """

    if request is None:
        raise HTTPException(status_code=400, detail="Request body cannot be empty")

    data = request

    # Backwards compatibility with previous eos-template service versions where [{"input": "value"}] was used.
    d0 = data[0]
    if isinstance(d0, dict):
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
        header = next(reader)
        for r in reader:
            R += [r]
    os.remove(input_file)
    os.remove(output_file)
    response = orient_to_json(R, header, data, orient)
    return response



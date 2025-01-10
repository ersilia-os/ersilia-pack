from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import FileResponse, JSONResponse
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


def get_prefix_from_info():
    """
    Extract the prefix from the get_info API.
    """
    info_response = get_info() 
    api_names = info_response.json().get("apis_list", [])

    if not api_names:
        raise HTTPException(status_code=404, detail="No API names found.")

    return api_names[0]


with open(os.path.join(bundle_folder, "information.json"), "r") as f:
    info_data = json.load(f)

output_type = info_data["card"]["Output Type"]
if output_type is None:
    output_type = ["String"]
if type(output_type) is str:
    output_type = [output_type]

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
    Get a predefined input example.
    """
    input_list = []
    prefix = get_prefix_from_info()
    file_to_open = None
   
    if os.path.exists(os.path.join(framework_folder, "examples", f"{prefix}_input.csv")):
        file_to_open = os.path.join(framework_folder, "examples", f"{prefix}_input.csv")
    elif os.path.exists(os.path.join(framework_folder, "examples", "input.csv")):
        file_to_open = os.path.join(framework_folder, "examples", "input.csv")
    else:
        raise HTTPException(status_code=404, detail="Example input file not found.")

    with open(file_to_open, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            input_list += row

    return input_list


@app.get("/example/output", tags=["Metadata"])
def example_output(orient: OrientEnum = Query(OrientEnum.records)):
    """
    Get a precalculated example output.
    """
    output_list = []
    prefix = get_prefix_from_info()
    file_to_open = None

    if os.path.exists(os.path.join(framework_folder, "examples", f"{prefix}_output.csv")):
        file_to_open = os.path.join(framework_folder, "examples", f"{prefix}_output.csv")
    elif os.path.exists(os.path.join(framework_folder, "examples", "output.csv")):
        file_to_open = os.path.join(framework_folder, "examples", "output.csv")
    else:
        raise HTTPException(status_code=404, detail="Example output file not found.")
 
    with open(file_to_open, "r") as f:
        reader = csv.reader(f)
        columns = next(reader)
        for r in reader:
            output_list += [r]
 
    with open(file_to_open, "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header
        index = []
        for r in reader:
            index += [r[0]]
 
    response = orient_to_json(output_list, columns, index, orient, output_type)
    return response


@app.get("/columns/input", tags=["Metadata"])
def columns_input():
    """
    Get the header of the input.
    """
    prefix = get_prefix_from_info()
    file_to_open = None

    if os.path.exists(os.path.join(framework_folder, "examples", f"{prefix}_input.csv")):
        file_to_open = os.path.join(framework_folder, "examples", f"{prefix}_input.csv")
    elif os.path.exists(os.path.join(framework_folder, "examples", "input.csv")):
        file_to_open = os.path.join(framework_folder, "examples", "input.csv")
    else:
        raise HTTPException(status_code=404, detail="Input example file not found.")
  
    with open(file_to_open, "r") as f:
        reader = csv.reader(f)
        return next(reader)


@app.get("/columns/output", tags=["Metadata"])
def columns_output():
    """
    Get the header of the output.
    """
    prefix = get_prefix_from_info()
    file_to_open = None

    if os.path.exists(os.path.join(framework_folder, "examples", f"{prefix}_output.csv")):
        file_to_open = os.path.join(framework_folder, "examples", f"{prefix}_output.csv")
    elif os.path.exists(os.path.join(framework_folder, "examples", "output.csv")):
        file_to_open = os.path.join(framework_folder, "examples", "output.csv")
    else:
        raise HTTPException(status_code=404, detail="Output example file not found.")

    with open(file_to_open, "r") as f:
        reader = csv.reader(f)
        return next(reader)

# TODO this will be extended when we incorporate more APIs 
@app.get("/info", tags=["Info"])
def get_info():
    """
    Get API information of the model
    """
    return JSONResponse(content={"apis_list": ["run"]})

# Post commands

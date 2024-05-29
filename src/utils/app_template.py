from fastapi import FastAPI, UploadFile, File
import uvicorn
import uuid
import json
import csv
import os
import argparse
import tempfile
import subprocess
from typing import Optional

root = os.path.dirname(os.path.abspath(__file__))
framework_folder = os.path.join(root, "model", "framework")
tmp_folder = tempfile.mkdtemp(prefix="ersilia-")

parser = argparse.ArgumentParser(description="ErsiliaAPI app")

parser.add_argument("--port", default=8000, type=int, help="An integer for the port")
parser.add_argument("--host", default="0.0.0.0", type=str, help="Host URL")

args = parser.parse_args()

with open(os.path.join(root, "info.json"), "r") as f:
    info_data = json.load(f)


app = FastAPI(
    title="{0}:{1}".format(info_data["card"]["Identifier"], info_data["card"]["Slug"]),
    description=info_data["card"]["Description"],
    version="latest",
)


# Deployment information. We may want to remove this.


@app.get("/framework", tags=["Deployment"])
def server():
    """
    Framework used, in this case, FastAPI

    """
    return "fastapi"


@app.get("/framework", tags=["Deployment"])
def host():
    """
    Host URL

    """
    return args.host


@app.get("/port", tags=["Deployment"])
def port():
    """
    Port

    """
    return args.port


# Metadata


@app.get("/info", tags=["Metadata"])
def info():
    """
    Get information for the Ersilia Model

    """
    return info_data


@app.get("/model_id", tags=["Metadata"])
def model_id():
    """
    Get model identifier

    """
    return info_data["card"]["model_id"]


@app.get("/slug", tags=["Metadata"])
def slug():
    """
    Get the slug

    """
    return info_data["card"]["slug"]


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


@app.post("/run", tags=["App"])
async def run(file: Optional[UploadFile] = File(...), data: Optional[list] = None):
    """
    Upload an input file to the server and run predictions or pass a list of inputs and run predictions.

    """
    tag = str(uuid.uuid4())
    if file is None and data is None:
        raise Exception("Please provide data, either as a file or as a list")
    if file is not None and data is not None:
        raise Exception(
            "Both a file and data were provided separately. Only one option is allowed at a time."
        )
    input_file = "{0}/{1}".format(tmp_folder, "input-{0}.csv".format(tag))
    if file is not None:
        with open(input_file, "wb") as buffer:
            buffer.write(await file.read())
    else:
        with open(input_file, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["input"])
            for r in data:
                writer.writerow([r])
    output_file = "{0}/{1}".format(tmp_folder, "output-{0}.csv".format(tag))
    cmd = "cd {0}; bash run.sh {1} {2}; cd {3}".format(
        framework_folder, input_file, output_file, root
    )
    subprocess.Popen(cmd, shell=True).wait()
    R = []
    with open(output_file, "r") as f:
        reader = csv.reader(f)
        for r in reader:
            R += [r]
    os.remove(input_file)
    os.remove(output_file)
    return R


if __name__ == "__main__":
    uvicorn.run("main:app", host=args.host, port=args.port, reload=True)

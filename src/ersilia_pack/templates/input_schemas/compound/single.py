import os
import csv
from typing import List, Dict, Union


root = os.path.dirname(os.path.abspath(__file__))


def read_example():
    """
    Read example input data.
    """
    file_to_open = None

    for filename in ["run_input.csv", "input.csv"]:
        path = os.path.join(root, "..", "model", "framework", "examples", filename)
        if os.path.exists(path):
            file_to_open = path
            break

    if not file_to_open:
        raise FileNotFoundError("No example input file found (run_input.csv or input.csv).")

    
    with open(file_to_open, "r") as f:
        reader = csv.reader(f)
        next(reader)  
        data = [x[0] for x in reader]
    return data
   


exemplary_input = read_example()[:3]

InputSchema = Union[List[str], List[Dict[str, str]]]

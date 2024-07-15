import os
import csv
from typing import List, Dict, Union


root = os.path.dirname(os.path.abspath(__file__))

def read_example():
    with open(os.path.join(root, "..", "model", "framework", "examples", "run_input.csv"), "r") as f:
        reader = csv.reader(f)
        next(reader)
        data = [x[0] for x in reader]
    return data    


exemplary_input = read_example()[:3]

InputSchema = Union[List[str], List[Dict[str, str]]]

import pytest
from ersilia_pack.templates.utils import orient_to_json

@ pytest.mark.parametrize("values, columns, index, orient, output_type, expected", [
    (
        [["1","2"], ["3","4"]],
        ["a","b"],
        [0,1],
        "split",
        ["integer"],
        {"columns":["a","b"],"index":[0,1],"data":[[1,2],[3,4]]}
    ),
    (
        [["0.0","","5.5"], [None,"7.2","8"]],
        ["x","y","z"],
        ["i","j"],
        "split",
        ["float"],
        {"columns":["x","y","z"],"index":["i","j"],"data":[[0.0,None,5.5],[None,7.2,8.0]]}
    ),
    (
        [["10","20"]],
        ["foo","bar"],
        ["idx"],
        "records",
        ["string"],
        [{"foo":"10","bar":"20"}]
    ),
    (
        [["1","2"], ["3","4"]],
        ["c1","c2"],
        ["r1","r2"],
        "index",
        ["integer"],
        {"r1":{"c1":1,"c2":2},"r2":{"c1":3,"c2":4}}
    ),
    (
        [["1","2"], ["3","4"]],
        ["c1","c2"],
        ["r1","r2"],
        "columns",
        ["integer"],
        {"c1":{"r1":1,"r2":3},"c2":{"r1":2,"r2":4}}
    ),
    (
        ["5","6","7.0"],
        ["a","b","c"],
        [0,1,2],
        "values",
        ["integer"],
        [5,6,7]
    ),
])
def test_orient_formats(values, columns, index, orient, output_type, expected):
    result = orient_to_json(values, columns, index, orient, output_type)
    assert result == expected


def test_multiple_output_type_defaults_to_string():
    res = orient_to_json(["x"], ["col"], [0], "values", ["int", "float"])
    assert res == ["x"]

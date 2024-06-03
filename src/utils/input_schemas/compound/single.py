from typing import List, Union, Dict
from pydantic import RootModel


class StringList(RootModel[List[str]]):
    pass


class DictList(RootModel[List[Dict[str, str]]]):
    pass


InputSchema = Union[StringList, DictList]

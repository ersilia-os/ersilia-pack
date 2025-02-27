from typing import List, Union

from pydantic import BaseModel, RootModel

from ...utils import read_example

exemplary_input = read_example()[:3]


class InputItem(BaseModel):
  key: str
  input: str


InputSchema = RootModel[Union[List[str], List[InputItem]]]

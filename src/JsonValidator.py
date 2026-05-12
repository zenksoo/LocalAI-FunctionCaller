from pydantic import BaseModel, Field
from typing import Dict


class TestCaseSchema(BaseModel):
    prompt: str = Field(min_length=1)


class FunctionDefSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Dict[str, str]]
    returns: Dict[str, str]

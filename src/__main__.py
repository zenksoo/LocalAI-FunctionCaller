from llm_sdk import Small_LLM_Model
from pathlib import Path
from .JsonValidator import TestCaseSchema, FunctionDefSchema
from typing import Dict, List, Any, Callable
from json.decoder import JSONDecodeError
from pydantic import ValidationError
import json
from sys import stderr
import sys
import argparse
from functools import singledispatch
from .Colors import *


def  errors_dispatch() -> Callable[[BaseException], None]:
    @singledispatch
    def dispatch(error_type: BaseException) -> None:
        print(error_type)

    @dispatch.register(ValidationError)
    def _(error) -> None:
        for error in error.errors():
            print(error)
            print("\n\n")
        print(f"Invalid Data: {error.errors()[0]["msg"]}", file=stderr)

    @dispatch.register(JSONDecodeError)
    def _(error) -> None:
        print(f"{BG_RED}{FG_BLACK}   Error Detected !   {RESET}\n")
        print(f"{BG_BLUE}  {RESET} Invalid Formate For JSON File: {error}", file=stderr)
        print("\n")

    return dispatch


def main() -> None:
    input_path = "./data/input/"
    ouput_path = "./data/ouput/"
    fdefinition = "functions_definition.json"
    input_f = "function_calling_tests.json"
    output_f = ""

    prompts = []
    with open("data/input/function_calling_tests.json", 'r') as f:
        content = json.load(f)
        for prompt in content:
            valid = TestCaseSchema(**prompt)
            prompts.append(valid.prompt)

    func_definition: List[FunctionDefSchema] = []
    with open("data/input/functions_definition.json", 'r') as f:
        content = json.load(f)
        for funcdef in content:
            valid = FunctionDefSchema(**funcdef)
            func_definition.append(valid)

    llm_model = Small_LLM_Model()

    for prompt in prompts:
        msg = f"prompt is : {prompt}, all functions : "
        msg += f"{[f.name for f in func_definition]}, what does the functino name that i use to solve what prompt tell me to do ? "
        encoded = llm_model.encode(msg).tolist()[0]
        while True:
            tokens = llm_model.get_logits_from_input_ids(encoded)
            new_token = tokens.index(max(tokens))
            encoded.append(new_token)
            print(llm_model.decode([new_token]), end="")
        return


    # string = prompts[0]
    # encoded = llm_model.encode(string).tolist()
    # encoded = encoded[0]
    # while True:
    #     tokens = llm_model.get_logits_from_input_ids(encoded)
    #     new_token = tokens.index(max(tokens))
    #     encoded.append(new_token)
    #     print(llm_model.decode([new_token]), end="")
    # except  as e:
    #     sys.exit(1)
    # except ValidationError as e:
    #     print(f"Invalid Data: {e.errors()[0]["msg"]}", file=stderr)
    #     sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="call-me-maybe it's ai model")
    parser.add_argument('-f', '--functions_definition')
    parser.add_argument('-i', '--input_file')
    parser.add_argument('-o', '--output_file')
    parser.add_argument('-v', '--verbose')
    args = parser.parse_args()
    # print(args.functions_definition)
    # print(args.input_file)
    # print(args.output_file)

    error_dispatch = errors_dispatch()

    try:
        main()
    except BaseException as e:
        error_dispatch(e)
        sys.exit(1)
    sys.exit(0)

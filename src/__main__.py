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


def get_error_handler() -> Callable[[BaseException], None]:
    @singledispatch
    def _handle_by_type(error_type: BaseException) -> None:
        print(f"{BG_BLUE} {RESET} {error_type}")

    @_handle_by_type.register(ValidationError)
    def _(exc: ValidationError) -> None:
        for error in exc.errors():
            if error["type"] == "missing":
                print(f"{BG_BLUE} {RESET} Missing",
                      f"Required Field: {', '.join([e for e in error["loc"]])}")
            else:
                print(f"{BG_BLUE} {RESET} {error["msg"]}")

    @_handle_by_type.register(JSONDecodeError)
    def _(exc: JSONDecodeError) -> None:
        print(f"{BG_BLUE} {RESET} Invalid Formate For JSON File: {exc}\n", file=stderr)

    @_handle_by_type.register(PermissionError)
    def _(exc: PermissionError) -> None:
        print(f"{BG_BLUE} {RESET} Permission Denied: {exc.filename}")

    @_handle_by_type.register(FileNotFoundError)
    def _(exc: FileNotFoundError) -> None:
        print(f"{BG_BLUE} {RESET} File not found: {exc.filename}")

    def render_exception(error: BaseException) -> None:
        print(f"\n{BG_RED}{FG_BLACK}   Program Failed !!   {RESET}", file=stderr, end="")
        print(f"{BG_YELLOW}{FG_BLACK} Error Type: {error.__class__.__name__} {RESET}")
        _handle_by_type(error)
        print()

    return render_exception


def encode_functions_name(funcs: List[FunctionDefSchema], llm_model: Small_LLM_Model) -> Dict[str, List[int]]:

    result: Dict[str, List[int]] = {}
    for func in funcs:
        result[func.name] = llm_model.encode(func.name).tolist()[0]
    return result



def main(args: argparse.Namespace) -> None:

    if not args.functions_definition:
        args.functions_definition = "functions_definition.json"
    if not args.input_file:
        args.input_file = "function_calling_tests.json"
    if not args.output_file:
        args.output_file = "function_calling_results.json"

    prompts: List[str] = []
    with open(f"data/input/{args.input_file}", 'r') as f:
        content = json.load(f)
        for prompt in content:
            valid = TestCaseSchema(**prompt)
            prompts.append(valid.prompt)

    func_definition: List[FunctionDefSchema] = []
    with open(f"data/input/{args.functions_definition}", 'r') as f:
        content = json.load(f)
        for funcdef in content:
            valid = FunctionDefSchema(**funcdef)
            func_definition.append(valid)

    llm_model = Small_LLM_Model()

    encoded_function_name = encode_functions_name(func_definition, llm_model)
    print(encoded_function_name)

    # tt: List[Dict[str, Any]] = []
    # i = 0
    # dic: Dict[str, Any] = {}
    # for func in func_definition:
    #     dic["name"] = func.name
    #     dic["parameters"] = func.parameters
    #     tt.append(dic)


    # for prompt in prompts:
    # mprompt = f"question: {prompts[0]}, function: fn_substitute_string_with_regex. this function solve the question ? "

    # msg = f"prompt is : {prompt}, all functions : "
    # msg += f"{[f.name for f in func_definition]}, what does the functino name that i use to solve what prompt tell me to do ? "
    # encoded = llm_model.encode(mprompt).tolist()[0]
    # # print(encoded)
    # while True:
    #     tokens = llm_model.get_logits_from_input_ids(encoded)
    #     new_token = tokens.index(max(tokens))
    #     encoded.append(new_token)
    #     print(llm_model.decode([new_token]), end="")


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

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--functions_definition')
    parser.add_argument('-i', '--input_file')
    parser.add_argument('-o', '--output_file')
    args = parser.parse_args()

    render_exception = get_error_handler()

    try:
        main(args)
    except BaseException as e:
        render_exception(e)
        sys.exit(1)
    sys.exit(0)

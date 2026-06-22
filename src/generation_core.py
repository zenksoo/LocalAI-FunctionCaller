from .rendering import render_progress_bar, get_msg_template
from llm_sdk import Small_LLM_Model
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from pathlib import Path
import numpy as np
import argparse
import json


RESET_TERMINAL = "\033[H\033[J"
SAVE_CURSOR_POSITION = "\033[s"
TO_SAVED_POSITION = "\033[u"
CLEAR_DOWN = "\033[J"


class TestCaseSchema(BaseModel):
    prompt: str = Field(min_length=1)


class FunctionDefSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Dict[str, str]]
    returns: Dict[str, str]


class Config(BaseModel):
    prompts: List[str] = []
    tools: List[dict[str, Any]] = []
    output_path: str
    input_path: str
    fn_definition_path: str

    @classmethod
    def load(cls) -> "Config":

        def get_prompts(input_path: str) -> List[str]:
            prompts: List[str] = []
            with open(input_path, 'r') as f:
                content = json.load(f)
                for prompt in content:
                    prompts.append(TestCaseSchema(**prompt).prompt)
            return prompts

        def get_functions_defschema(fndef_path: str) -> List[Dict[str, Any]]:
            fncs_definition: List[Dict[str, Any]] = []
            with open(fndef_path, 'r') as f:
                content = json.load(f)
                for fndef in content:
                    fndef_schema = FunctionDefSchema(**fndef)
                    fncs_definition.append({
                            "name": fndef_schema.name,
                            "description": fndef_schema.description,
                            "parameters": fndef_schema.parameters,
                            "returns": fndef_schema.returns
                        }
                    )
            return fncs_definition

        agparser = argparse.ArgumentParser()
        agparser.add_argument(
            '-f', '--functions_definition',
            help="Path to JSON file that contain functions definition",)
        agparser.add_argument(
            '-i', '--input',
            help="Path to JSON file that contains prompts that \
                you want the LLM to process")
        agparser.add_argument(
            '-o', '--output',
            help="Where you want to save the LLM output")
        args = agparser.parse_args()
        if not args.functions_definition:
            args.functions_definition = "data/input/functions_definition.json"
        if not args.input:
            args.input = "data/input/function_calling_tests.json"
        if not args.output:
            args.output = "data/output/function_calling_results.json"

        return Config(prompts=get_prompts(args.input),
                      tools=get_functions_defschema(args.functions_definition),
                      output_path=args.output,
                      input_path=args.input,
                      fn_definition_path=args.functions_definition)

    def write_results(self, results: List[Dict[str, Any]]) -> None:
        path = "/".join(self.output_path.split("/")[:-1])

        Path(path).mkdir(parents=True, exist_ok=True)
        with open(self.output_path, 'w') as file:
            json.dump(results, file, indent=4)


class ToolRegistry(BaseModel):
    tools: List[Dict[str, Any]] = []

    def build_fn_prompt(self, user_request: str) -> str:
        def function_with_description() -> Dict[str, str]:
            return {e["name"]: e["description"] for e in self.tools}

        available_functions = function_with_description()
        return f"""You are a function-calling assistant. \
Given a user request, pick the best function \
and return ONLY a JSON object of the right function name \
and none if no function matche the user request
Available functions:
    {available_functions}

If no function description matches the user request the functino\
 name will be 'none'

User request:
    {user_request}

Response:
        """

    def build_param_prompt(self, user_request: str, function_name: str) -> str:
        def function_with_parameters() -> Dict[str, str]:
            return {
                function_name: e["parameters"]
                for e in self.tools if e["name"] == function_name}

        available_functions = function_with_parameters()
        return f"""you are function parameter generator

chosen function parameter:
{available_functions}


Rules for filling parameters:
- Regex character classes MUST be wrapped in square brackets: [abc] not abc
- NEVER use the English word for a symbol — always use the symbol itself
- "replace","substitute","swap","change","convert" all mean the same operation

Examples for filling parameters:
request: Replace all numbers in "hi 42 bye" with NUM
response:{{"parameters": {{"source_string": "hi 42 bye",\
    "regex": "[0-9]+", "replacement": "NUM"}}}}

request: Replace vowels in "hello world" with asterisks
response: {{"parameters": \
    {{\
        "source_string": "hello world", \
        "regex": "[aeiouAEIOU]", "replacement": "*"}}}}

request: Replace 'cat' with 'dog' in "the cat sat"
response: {{"parameters": {{\
        "source_string": "the cat sat", \
        "regex": "cat", "replacement": "dog"}}}}

request: Substitute all spaces in "hello world foo" with dashes
response: {{"parameters": {{"source_string": "hello world foo",\
"regex": "[ ]+", "replacement": "-"}}}}

User request:
    {user_request}
Response:
        """

    def get_valid_names(self) -> List[str]:
        return [t["name"] for t in self.tools]

    def get_valid_parameters(self) -> Dict[str, List[str]]:
        fn_names = self.get_valid_names()
        fn_para = [t["parameters"] for t in self.tools]
        return {key: list(val.keys()) for key, val in zip(fn_names, fn_para)}


# generate function name for the given prompt
class ConstrainedFnGenerator(BaseModel):
    def generate(self, model: Small_LLM_Model,
                 prompt: str, registry: ToolRegistry,
                 with_animation: bool = True,
                 max_new_tokens: int = 200) -> Any:
        prompt = registry.build_fn_prompt(prompt)
        valid_names = registry.get_valid_names()
        valid_names.append("none")

        input_ids = model._tokenizer.encode(prompt, add_special_tokens=False)
        generated = model._tokenizer.encode("{\"name\": \"")

        input_ids += generated

        state = 1
        fn_name_generated: str = ""
        pre_injected_token_str = "{\"name\"}: \""

        if with_animation:
            get_msg_template("red")("STEP 1", "Function name Generation")
            print(SAVE_CURSOR_POSITION)

        for i in range(max_new_tokens):
            logits = np.array(model.get_logits_from_input_ids(input_ids))
            token_id = 0
            while (state == 1 and token_id < len(logits)):
                token_str = model._tokenizer.decode([token_id])
                condidate = fn_name_generated + token_str

                is_prefix = any(n.startswith(condidate) for n in valid_names)
                is_exact = condidate in valid_names

                if not is_prefix and not is_exact:
                    logits[token_id] = -float('inf')
                token_id += 1

            if np.all(logits == -float('inf')):
                pre_injected_token = model._tokenizer.encode("none")
                input_ids += pre_injected_token
                generated += pre_injected_token
                next_token = model._tokenizer.encode("\"}")
            else:
                next_token = int(np.argmax(logits))

            input_ids.append(next_token)
            generated.append(next_token)

            token_str = model._tokenizer.decode(next_token)
            if with_animation:
                print(TO_SAVED_POSITION, CLEAR_DOWN)
                render_progress_bar(i)
                get_msg_template("cyan")("LLM TOKEN   ", f"'{token_str}'")
            generated_str = model._tokenizer.decode(
                generated, skip_special_tokens=True)
            if with_animation:
                get_msg_template("green")(
                    "Per Injected", f"'{pre_injected_token_str}'")
                get_msg_template("yellow")("Response    ", generated_str)
                pre_injected_token_str = ""

            if (generated_str.count('{') > 0 and
               generated_str.count('}') >= generated_str.count('{')):
                break

            if state == 1:
                fn_name_generated += token_str
                if fn_name_generated in valid_names:
                    pre_injected_token = model._tokenizer.encode("\"}")
                    input_ids += pre_injected_token
                    generated += pre_injected_token
                    state = 0

        if with_animation:
            print(TO_SAVED_POSITION, CLEAR_DOWN)
            get_msg_template("yellow")("RESULT", generated_str)
        return json.loads(generated_str)


# generate function parameter base on function name that
# selected by ConstrainedFnGenerator
class ConstrainedParGenerator(BaseModel):
    def generate(self, model: Small_LLM_Model, prompt: str,
                 function_name: str, registry: ToolRegistry,
                 with_animation: bool = True,
                 max_new_tokens: int = 200) -> Any:
        prompt = registry.build_param_prompt(prompt, function_name)
        valid_parameters: List = []
        for fn in registry.tools:
            if fn["name"] == function_name:
                valid_parameters = list(fn["parameters"].keys())

        input_ids = model._tokenizer.encode(prompt, add_special_tokens=True)
        generated = model._tokenizer.encode("{\"parameters\": {\"")
        input_ids += (generated)

        state = 0
        parameter_name = ""
        pre_injected_token_str = "{\"parameters\": {\""

        if with_animation:
            get_msg_template("red")("STEP 2", "Function Parameters Generation")
            print(SAVE_CURSOR_POSITION)

        for i in range(max_new_tokens):
            logits = np.array(model.get_logits_from_input_ids(input_ids))
            token_id = 0
            while (state == 0 and token_id < len(logits)):
                token_str = model._tokenizer.decode([token_id])
                condidate = parameter_name + token_str

                is_prefix = any(
                    n.startswith(condidate) for n in valid_parameters)
                is_exact = condidate in valid_parameters

                if not is_prefix and not is_exact:
                    logits[token_id] = -float('inf')

                token_id += 1

            if np.all(logits == -float('inf')):
                if state == 0:
                    next_token = model._tokenizer.encode("}}")[0]
            else:
                next_token = int(np.argmax(logits))

            token_str = model._tokenizer.decode(
                next_token, skip_special_tokens=True)
            if with_animation:
                print(TO_SAVED_POSITION, CLEAR_DOWN)
                render_progress_bar(i)
                get_msg_template("cyan")("LLM TOKEN   ", f"'{token_str}'")

            if (state != 1 or "," not in token_str or
               len(valid_parameters) != 0):
                input_ids.append(next_token)
                generated.append(next_token)

            if state == 0:
                parameter_name += token_str

                if parameter_name in valid_parameters:
                    pre_injected_token_str = "\": "
                    pre_injected_token = model._tokenizer.encode("\": ")
                    input_ids += pre_injected_token
                    generated += pre_injected_token
                    valid_parameters.remove(parameter_name)
                    parameter_name = ""
                    state = 1

            elif state == 1 and "," in token_str:
                if len(valid_parameters) == 0:
                    if token_str.startswith("\""):
                        input_ids += model._tokenizer.encode("\"")
                        generated += model._tokenizer.encode("\"")

                    input_ids += model._tokenizer.encode("}}")
                    generated += model._tokenizer.encode("}}")
                else:
                    input_ids += model._tokenizer.encode(" \"")
                    generated += model._tokenizer.encode(" \"")
                state = 0

            generated_str = model._tokenizer.decode(
                generated, skip_special_tokens=True)
            if with_animation:
                get_msg_template("green")(
                    "Per Injected", f"'{pre_injected_token_str}'")
                get_msg_template("yellow")("Response    ", generated_str)
                pre_injected_token_str = ""
            if (generated_str.count('{') > 0 and
               generated_str.count('}') >= generated_str.count('{')):
                break

        if with_animation:
            print(TO_SAVED_POSITION, CLEAR_DOWN)
            get_msg_template("yellow")("RESULT", generated_str)
        return json.loads(generated_str)

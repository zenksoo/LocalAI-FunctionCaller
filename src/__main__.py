from .rendering import (get_error_handler, render_progress_bar,
                        get_msg_template, render_prompts_stat)
from .JsonValidator import TestCaseSchema, FunctionDefSchema
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
from llm_sdk import Small_LLM_Model
import numpy as np
import argparse
import json
import sys
import time


# Move cursor to the top left and clear everything below it
RESET_TERMINAL = "\033[H\033[J"
SAVE_CURSOR_POSITION = "\033[s"
TO_SAVED_POSITION = "\033[u"
CLEAR_DOWN = "\033[J"


class Config(BaseModel):
    prompts: List[str] = []
    tools: List[dict[str, Any]] = []
    output_path: str

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
                      output_path=args.output)

    def write_results(self, results: List[Dict[str, Any]]) -> None:
        path = "/".join(self.output_path.split("/")[:-1])

        Path(path).mkdir(parents=True, exist_ok=True)
        with open(self.output_path, 'w') as file:
            json.dump(results, file, indent=4)


class ToolRegistry(BaseModel):
    tools: List[Dict[str, Any]] = []

    def build_prompt(self, user_request: str) -> str:
        tools_json = json.dumps(self.tools, indent=2)
        return f"""You are a function-calling assistant. \
Given a user request, pick the best function \
and return ONLY a JSON object — no explanation, no markdown, no extra text.

Available functions:
{tools_json}

Rules for filling parameters:
- For regex parameters: construct a proper regex pattern (e.g. [0-9]+ for \
    digits) — do NOT copy raw words unless the user is matching a literal word
- For replacement parameters: use the exact replacement CHARACTER, not its \
    name (if name have character meaning)
  (e.g. "asterisks" → "*", "hash" → "#", "dash" → "-", "underscore" → "_")

Output format (strictly): \
{{"function": "<function_name>", "parameters": {{<key>: <value>, ...}}}}

If no function description matches the user request, return exactly: \
{{"function": "NONE", "parameters": {{}}}}

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


class ConstrainedGenerator(BaseModel):
    def generate(self, model: Small_LLM_Model, prompt: str,
                 registry: ToolRegistry, max_new_tokens: int = 200
                 ) -> Dict[str, str]:
        prompt = registry.build_prompt(prompt)
        valid_names = registry.get_valid_names()
        valid_names.append("NONE")
        valid_parameters = registry.get_valid_parameters()

        input_ids = model._tokenizer.encode(prompt, add_special_tokens=False)
        eos_id = model._tokenizer.eos_token_id

        generated: List[int] = model._tokenizer.encode(
            "{\"function\": \"", add_special_tokens=False)
        input_ids += generated
        state = 0
        fn_name_generated: str = ""
        parameters: List[str] = []
        parameter_name: str = ""

        print(SAVE_CURSOR_POSITION)

        for i in range(max_new_tokens):
            logits = np.array(model.get_logits_from_input_ids(input_ids))
            token_id = 0

            while (state == 0 and token_id < len(logits)):
                token_str = model._tokenizer.decode([token_id])
                condidate = fn_name_generated + token_str

                is_prefix = any(n.startswith(condidate) for n in valid_names)
                is_exact = condidate in valid_names

                if not is_prefix and not is_exact:
                    logits[token_id] = -float('inf')
                token_id += 1

            while (state == 1 and token_id < len(logits)):
                token_str = model._tokenizer.decode([token_id])
                condidate = parameter_name + token_str
                fname = fn_name_generated
                is_prefix = any(
                    n.startswith(condidate) for n in valid_parameters[fname])
                is_exact = condidate in valid_parameters[fn_name_generated]

                if not is_prefix and not is_exact:
                    logits[token_id] = -float('inf')
                token_id += 1

            if np.all(logits == -float('inf')):
                if state == 0:
                    pre_injected_token = model._tokenizer.encode("\"}")
                    input_ids += pre_injected_token
                    generated += pre_injected_token
                    get_msg_template("green")("Per Injected", "'\"}'")
                    break
                else:
                    next_token = model._tokenizer.encode("}}")[0]
            else:
                next_token = int(np.argmax(logits))

            if next_token == eos_id:
                break

            token_str = model._tokenizer.decode(
                [next_token], skip_special_tokens=True)

            input_ids.append(next_token)
            generated.append(next_token)

            generated_str = model._tokenizer.decode(
                generated, skip_special_tokens=True)
            print(TO_SAVED_POSITION, CLEAR_DOWN)
            render_progress_bar(i)
            get_msg_template("cyan")("LLM TOKEN", f"\"{token_str}\"")

            if (generated_str.count('{') > 0 and
               generated_str.count('}') >= generated_str.count('{')):
                break

            if state == 0:
                fn_name_generated += token_str
                if fn_name_generated in valid_names:
                    if fn_name_generated == "NONE":
                        pre_injected_token = model._tokenizer.encode("\"}")
                        get_msg_template("green")("Per Injected", "'\"}'")
                        input_ids += pre_injected_token
                        generated += pre_injected_token
                        break
                    pre_injected_token = model._tokenizer.encode(
                        "\", \"parameters\": {")
                    if len(valid_parameters[fn_name_generated]) > 0:
                        pre_injected_token += model._tokenizer.encode("\"")
                    input_ids += pre_injected_token
                    generated += pre_injected_token
                    get_msg_template("green")(
                        "Per Injected Tokens", "'\", \"parameters\": {'")
                    state = 1
            elif state == 1:
                parameter_name += token_str
                if parameter_name in valid_parameters[fn_name_generated]:
                    pre_injected_token = model._tokenizer.encode("\": ")
                    input_ids += pre_injected_token
                    generated += pre_injected_token
                    parameters.append(parameter_name)
                    parameter_name = ""
                    state = 2
                    get_msg_template("green")("Per Injected", "'\": '")

            elif state == 2:
                if "," in token_str:
                    input_ids += model._tokenizer.encode(" \"")
                    generated += model._tokenizer.encode(" \"")
                    state = 1

            get_msg_template("yellow")("Response", generated_str)

        json_generated = json.loads(generated_str)
        result = {"prompt": ""}

        if fn_name_generated != "NONE" and fn_name_generated in valid_names:
            result["name"] = json_generated["function"]
            if parameters == valid_parameters[fn_name_generated]:
                result["parameters"] = json_generated["parameters"]
            else:
                result["parameters"] = "invalid parameters"
        else:
            result["name"] = "invalid function name"

        return result


if __name__ == "__main__":
    render_exception = get_error_handler()
    try:
        config = Config.load()
        registry = ToolRegistry(tools=config.tools)

        constrained_gen = ConstrainedGenerator()
        model = Small_LLM_Model()

        results: List[Dict[str, Any]] = []
        passed_prompts: List[bool] = []

        start = time.perf_counter()
        for prompt in config.prompts:
            response: Dict[str, str] = {}

            print(RESET_TERMINAL)
            render_prompts_stat(config.prompts, passed_prompts)
            get_msg_template("green")("PROMPT", prompt)
            try:
                response = constrained_gen.generate(model, prompt, registry)
                response["prompt"] = prompt
                passed_prompts.append(True)
            except KeyboardInterrupt:
                response["prompt"] = prompt
                response["error"] = "Skip Generating"
                passed_prompts.append(False)
            results.append(response)

        render_prompts_stat(config.prompts, passed_prompts)

        end = time.perf_counter()
        exuction_time = (end - start) / 60
        with open("excution_time.txt", 'w') as f:
            f.write(f"{exuction_time:.6f}")

        config.write_results(results)
    except SystemExit:
        pass
    except (BaseException, KeyboardInterrupt) as e:
        render_exception(e)
        sys.exit(1)
    sys.exit(0)

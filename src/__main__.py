from .rendering import get_error_handler
from .JsonValidator import TestCaseSchema, FunctionDefSchema
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Callable
from pathlib import Path
from llm_sdk import Small_LLM_Model
import numpy as np
import argparse
import json
import sys
import re


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
        agparser.add_argument('-f', '--functions_definition',
                            help="Path to JSON file that contain functions definition",)
        agparser.add_argument('-i', '--input',
                            help="Path to JSON file that contains prompts that \
                                you want the LLM to process")
        agparser.add_argument('-o', '--output',
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

    def build_prompt(self, user_request: str):
        tools_json = json.dumps(self.tools, indent=2)
        return f"""You are a function-calling assistant. \
        Given a user request, pick the best function \
        and return ONLY a JSON object — no explanation, no markdown, no extra text.

        Available functions:
{tools_json}

        Output format (strictly): \
{{"function": "<function_name>", "parameters": {{<key>: <value>, ...}}}}

        If no function matches, return exactly:
        {{"function": "", "parameters": {{}}}}

        User request: {user_request}
        Response:

        """

    def get_valid_names(self) -> List[str]:
        return [t["name"] for t in self.tools]

    def get_valid_parameters(self) -> Dict[str, List[str]]:
        fn_names = self.get_valid_names()
        fn_para = [t["parameters"] for t in self.tools]
        return {key: list(val.keys()) for key, val in zip(fn_names, fn_para)}

    def parse_tool_call(self, raw: str) -> Any:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in model output:\n{raw}")
        return json.loads(match.group())

    def validate_call(self, raw: Dict[str, Any]) -> bool:
        index = next((i for i, d in enumerate(self.tools) if d.get("name") == raw.get("function")), None)
        if index is None:
            return False
        registerd_param = self.tools[index]["parameters"].keys()
        response_param = raw["parameters"].keys()
        if registerd_param != response_param:
            return False
        return True


class ConstrainedGenerator(BaseModel):
    def generate(self, model: Small_LLM_Model, prompt: str, valid_names: List[str], max_new_tokens: int = 200) -> Any:
        parameters = ""

        input_ids = model._tokenizer.encode(prompt, add_special_tokens=False)
        eos_id = model._tokenizer.eos_token_id

        generated: List[int] = model._tokenizer.encode("{\"function\": \"", add_special_tokens=False)
        input_ids += generated
        state = 0
        fn_name_generated = ""
        for i in range(max_new_tokens):
            logits = np.array(model.get_logits_from_input_ids(input_ids))
            if state == 0:
                for token_id in range(len(logits)):
                    token_str = model._tokenizer.decode([token_id])
                    condidate = fn_name_generated + token_str


                    is_prefix = any(n.startswith(condidate) for n in valid_names)
                    is_exact = condidate in valid_names

                    if not is_prefix and not is_exact:
                        logits[token_id] = -float('inf')
                if np.all(logits == -float('inf')):
                    raise ValueError(f"No function matched the request.")

            next_token = int(np.argmax(logits))

            if next_token == eos_id:
                break

            token_str = model._tokenizer.decode([next_token], skip_special_tokens=True)
            if state == 1:
                parameters += token_str
            print(f"#{token_str}#")

            input_ids.append(next_token)
            generated.append(next_token)

            partial = model._tokenizer.decode(generated, skip_special_tokens=True)
            if partial.count('{') > 0 and partial.count('}') >= partial.count('{'):
                break

            if state == 0:
                fn_name_generated += token_str
                if fn_name_generated in valid_names:
                    input_ids += model._tokenizer.encode("\", \"parameters\": {\"")
                    generated += model._tokenizer.encode("\", \"parameters\": {\"")
                    chosen_fn = fn_name_generated
                    state = 1

        return model._tokenizer.decode(generated, skip_special_tokens=True)



class FunctionCaller(BaseModel):
    registry: ToolRegistry

    def run(self, prompt: str) -> Any:
        constrained_gen = ConstrainedGenerator()
        model = Small_LLM_Model()

        prompt = registry.build_prompt(prompt)
        response = constrained_gen.generate(model, prompt, registry.get_valid_names())
        print(f"the response is : {response}")
        json_response = registry.parse_tool_call(response)
        print(f"the jsonresponse is : {json_response}")
        if not registry.validate_call(json_response):
            json_response = None
        return json_response

if __name__ == "__main__":
    render_exception = get_error_handler()
    try:
        config = Config.load()
        registry = ToolRegistry(tools=config.tools)
        print(registry.get_valid_parameters())

        caller = FunctionCaller(registry=registry)

        results: List[Dict[str, Any]] = []
        passed_promts: List[bool] = []
        for prompt in config.prompts:
            raw = caller.run(prompt)
            if raw:
                results.append({
                    "prompt": prompt,
                    "name": raw["function"],
                    "parameters": raw["parameters"]
                })
                passed_promts.append(True)
            else:
                passed_promts.append(False)
            print(passed_promts)

        config.write_results(results)
    except SystemExit:
        pass
    except (BaseException, KeyboardInterrupt) as e:
        render_exception(e)
        sys.exit(1)
    sys.exit(0)

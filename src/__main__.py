from llm_sdk import Small_LLM_Model
from src.JsonValidator import TestCaseSchema, FunctionDefSchema
import numpy as np
import argparse
import sys
from typing import Dict, List, Any
from pathlib import Path
import time
import json
import re
from src.rendering import get_error_handler, render_progress_bar
from src.rendering import render_prompts_stat


RESET = "\033[0m"

# Foreground colors
FG_BLACK = "\033[30m"
FG_RED = "\033[31m"
FG_GREEN = "\033[32m"

# Background colors
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_BLUE = "\033[44m"
BG_CYAN = "\033[46m"


def parse_functions_definitions(funcs: List[FunctionDefSchema]
                                ) -> List[Dict[str, Any]]:
    TOOLS: List[Dict[str, Any]] = []
    for f in funcs:
        TOOLS.append(
            {
                "name": f.name,
                "description": f.description,
                "parameters": f.parameters,
                "returns": f.returns
            },
        )
    return TOOLS


def build_prompt(user_request: str, tools: List[Dict[str, Any]]) -> str:
    tools_json = json.dumps(tools, indent=2)
    return f"""You are a function-calling assistant.
    Given a user request, pick the best function
    and return ONLY a JSON object — no explanation, no markdown, no extra text.

            Available functions:
            {tools_json}

            Output format (strictly):
            {{"function": "<function_name>",
            "parameters": {{<key>: <value>, ...}}}}

            User request: {user_request}
            Response:
        """


def generate(model: Small_LLM_Model,
             prompt: str, max_new_tokens: int = 200) -> Any:
    # Encode prompt → list of ints
    input_ids = model._tokenizer.encode(prompt, add_special_tokens=False)
    eos_id = model._tokenizer.eos_token_id

    generated = []
    for i in range(max_new_tokens):
        logits = model.get_logits_from_input_ids(input_ids)

        # pick the token with the highest logit
        next_token = int(np.argmax(logits))

        if next_token == eos_id:
            break

        input_ids.append(next_token)
        generated.append(next_token)

        # # Stop early if we see a closing brace → JSON is done
        partial = model._tokenizer.decode(generated, skip_special_tokens=True)
        if partial.count('{') > 0 and partial.count('}') >= partial.count('{'):
            break
        render_progress_bar(i)
    sys.stdout.write("\033[?25h\r\033[K")

    return model._tokenizer.decode(generated, skip_special_tokens=True)


def parse_tool_call(raw: str) -> Any:
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in model output:\n{raw}")
    return json.loads(match.group())


def run(model: Small_LLM_Model, user_request: str,
        output_res: List[Dict[str, Any]],
        tools: List[Dict[str, Any]]) -> bool:
    prompt = build_prompt(user_request, tools)
    raw = generate(model, prompt)
    time.sleep(0.05)

    call = parse_tool_call(raw)
    fn_name = call["function"]
    params = call["parameters"]

    output_res.append(
        {
            "prompt": user_request,
            "name": fn_name,
            "parameters": params
        }
    )
    return True


def main(args: argparse.Namespace) -> None:

    if not args.functions_definition:
        args.functions_definition = "functions_definition.json"
    if not args.input_file:
        args.input_file = "function_calling_tests.json"
    if not args.output_file:
        args.output_file = "function_calling_results.json"

    output_path = Path("data/output")

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

    TOOLS = parse_functions_definitions(func_definition)

    llm_model = Small_LLM_Model()

    output_res: List[Dict[str, Any]] = []
    passed_prompt: List[bool] = []
    for p, i in zip(prompts, range(1, len(prompts) + 1)):
        try:
            sys.stdout.write("\033[2J\033[H\033[?25l")
            sys.stdout.flush()
            render_prompts_stat(i, prompts, passed_prompt)

            print(f"\n{BG_BLUE} {RESET}{BG_CYAN}{FG_BLACK} Prompt {RESET} {p}")
            try:
                res = run(llm_model, p, output_res, TOOLS)
            except KeyboardInterrupt:
                res = False
            passed_prompt.append(res)
            time.sleep(0.08)
        except KeyboardInterrupt:
            pass

    sys.stdout.write("\033[2J\033[H\033[?25l")
    sys.stdout.flush()
    render_prompts_stat(len(prompts) + 1, prompts, passed_prompt)

    if any(passed_prompt):
        output_path.mkdir(parents=True, exist_ok=True)
        with open(f"data/output/{args.output_file}", 'w') as f:
            json.dump(output_res, f, indent=4)
        print(f"\n\n{BG_GREEN} {RESET} {FG_GREEN}",
              f"Passed Prompts Are Seccessfully Saved{RESET}")
        print(f"{BG_GREEN} {RESET} PATH: /data/ouput/{args.output_file}")
        sys.stdout.write("\033[?25h")
    else:
        print(f"\n\n{BG_RED} {RESET}{FG_RED}",
              f"All Prompts Failed Nothing to save{RESET}")


if __name__ == "__main__":
    render_exception = get_error_handler()
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-f', '--functions_definition')
        parser.add_argument('-i', '--input_file')
        parser.add_argument('-o', '--output_file')
        args = parser.parse_args()

        main(args)
    except (BaseException, KeyboardInterrupt) as e:
        render_exception(e)
        sys.exit(1)
    sys.exit(0)

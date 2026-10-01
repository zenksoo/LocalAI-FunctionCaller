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


class GenerationConfig(BaseModel):
    """
    Configuration class for the generation process.
    """
    prompts: List[str] = []
    tools: List[dict[str, Any]] = []
    output_path: str
    input_path: str
    fn_definition_path: str

    @classmethod
    def load(cls) -> "GenerationConfig":
        """
        Loads the configuration from command-line arguments.

        Returns:
            GenerationConfig: An instance of the GenerationConfig class with loaded settings.
        """

        def get_prompts(input_path: str) -> List[str]:
            """ Gets the prompts from a JSON file.

            Args:
                input_path (str): Path to the JSON file containing prompts.

            Returns:
                List[str]: A list of prompts.
            """
            prompts: List[str] = []
            with open(input_path, 'r') as f:
                content = json.load(f)
                for prompt in content:
                    prompts.append(TestCaseSchema(**prompt).prompt)
            return prompts

        def get_functions_defschema(fndef_path: str) -> List[Dict[str, Any]]:
            """ Gets the function definitions from a JSON file.

            Args:
                fndef_path (str): Path to the JSON file containing function
                                definitions.

            Returns:
                List[Dict[str, Any]]: A list of dictionaries representing
                                    `function definitions.
            """
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

        return GenerationConfig(
            prompts=get_prompts(args.input),
            tools=get_functions_defschema(args.functions_definition),
            output_path=args.output,
            input_path=args.input,
            fn_definition_path=args.functions_definition)

    def write_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Writes the results to the specified output path in JSON format.

        Args:
            results (List[Dict[str, Any]]): A list of dictionaries containing
                                            the results to be written.
        """

        path = "/".join(self.output_path.split("/")[:-1])

        Path(path).mkdir(parents=True, exist_ok=True)
        with open(self.output_path, 'w') as file:
            json.dump(results, file, indent=4)


class ToolRegistry(BaseModel):
    tools: List[Dict[str, Any]] = []

    def build_fn_prompt(self, user_request: str) -> str:
        """
        Builds a prompt for function name generation based on the user request.

        Args:
            user_request (str): The user request for which the function name
                                needs to be generated.

        Returns:
            str: The generated prompt for function name generation.
        """
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
        """
        Builds a prompt for function parameter generation based on
        the user request and function name.

        Args:
            user_request (str): The user request for which the function
                                parameters need to be generated.
            function_name (str): The name of the function for which the
                                parameters need to be generated.

        Returns:
            str: The generated prompt for function parameter generation.
        """
        # def function_with_parameters() -> Dict[str, str]:
        #     """
        #     Returns a dictionary mapping function names to their parameters.
        #     """
        function_description = ""
        function_parameters = {}

        for tool in self.tools:
            if (tool["name"] == function_name):
                function_description = tool["description"]
                function_parameters = tool["parameters"]

#         return f"""you are function parameter generator

# chosen function parameter:
# {available_functions}

# the parameter name and his value much the type of parameter above no extra parameter outside the function


# Rules for filling parameters:
# - Regex character classes MUST be wrapped in square brackets: [abc] not abc
# - NEVER use the English word for a symbol — always use the symbol itself
# - "replace","substitute","swap","change","convert" all mean the same operation

# User request:
#     {user_request}
# Response:
#         """

#         return f"""Extract the arguments for ONE function call from the user request.
# Output a single JSON object containing the parameter values. Nothing else.

# Function: {function_name}
# Description: {function_description}
# Parameters:
# {function_parameters}

# Rules:
# 1. Output exactly the parameters listed above: same names, none missing, no extras.
# 2. Match the types: string -> JSON string, number -> JSON number (no quotes),
#    integer -> whole number, boolean -> true or false.
# 3. Copy values from the request exactly (spelling, case, spacing).
#    Never translate, correct, or invent values.
# 4. Symbols: write the symbol itself, never its name.
#    "asterisk" -> "*", "dollar sign" -> "$", "dot" -> ".", "dash" -> "-"
# 5. Regex: always use square-bracket character classes, never backslash shortcuts.
#    digits -> [0-9]+   letters -> [a-zA-Z]+   vowels -> [aeiouAEIOU]
#    a space -> [ ]
# 6. "replace", "substitute", "swap", "change", "convert" all mean replace.
#    The text to find is the regex. The new text is the replacement.
# 7. Numbers allways float when number is int like 8 convert it to 8.0
# Request: {user_request}
# Output: """

        return f"""You extract arguments for one selected function.

The user request is:
{user_request}

Selected function:
{function_name}

Function description:
{function_description}

Required parameters and types:
{json.dumps(function_parameters, indent=2)}

The decoder has already started the JSON output with:
{{"parameters": {{

Rules:
1. Generate values only for the parameters listed above.
2. Use every parameter exactly once, with the exact parameter name.
3. Do not add, remove, rename, or reorder parameters.
4. Match each declared JSON type exactly:
   - string -> JSON string
   - number -> JSON number
   - integer -> JSON integer
   - boolean -> true or false
5. Copy values from the user request exactly. Preserve spelling, case,
   spaces, punctuation, and special characters.
6. Do not explain your answer.
7. Do not output Markdown or code fences.
8. Do not output the function name.
9. Do not output the opening JSON object; it is already provided.
10. Finish with valid JSON-compatible values only.

User request:
{user_request}

Continue the parameters object now.
"""

    def get_valid_names(self) -> List[str]:
        """ Returns a list of valid function names."""
        return [t["name"] for t in self.tools]

    def get_valid_parameters(self) -> Dict[str, List[str]]:
        """
        Returns a dictionary mapping function names to their valid
        parameters.
        """
        fn_names = self.get_valid_names()
        fn_para = [t["parameters"] for t in self.tools]
        return {key: list(val.keys()) for key, val in zip(fn_names, fn_para)}


# generate function name for the given prompt
class ConstrainedFunctionNameGenerator(BaseModel):
    def generate(self, model: Small_LLM_Model,
                 prompt: str, registry: ToolRegistry,
                 with_animation: bool = True,
                 max_new_tokens: int = 200) -> Any:

        """
        Generates a function name based on the given prompt using the
        provided model and registry.

        Args:
            model (Small_LLM_Model): The language model used for generation.
            prompt (str): The user request for which the function name needs
                          to be generated.
            registry (ToolRegistry): The registry containing available
                                     functions and their details.
            with_animation (bool, optional): Whether to display progress
                                             animation. Defaults to True.
            max_new_tokens (int, optional): Maximum number of tokens to
                                            generate. Defaults to 200.

        Returns:
            Any: The generated function name.
        """

        prompt = registry.build_fn_prompt(prompt)
        valid_names = registry.get_valid_names()
        valid_names.append("none")

        input_ids = model._tokenizer.encode(prompt, add_special_tokens=False)
        generated = model._tokenizer.encode("{\"name\": \"")

        input_ids += generated

        # state 1: generating function name
        # state 0: generating parameters
        state = 1
        fn_name_generated: str = ""
        pre_injected_token_str = "{\"name\"}: \""

        generated_str = ""

        if with_animation:
            get_msg_template("red")("STEP 1", "Function name Generation")
            print(SAVE_CURSOR_POSITION)

        for i in range(max_new_tokens):
            logits = np.array(model.get_logits_from_input_ids(input_ids))
            token_id = 0
            # constrain the logits to only valid function names
            while (state == 1 and token_id < len(logits)):
                token_str = model._tokenizer.decode([token_id])
                condidate = fn_name_generated + token_str

                is_prefix = any(n.startswith(condidate) for n in valid_names)
                is_exact = condidate in valid_names

                if not is_prefix and not is_exact:
                    logits[token_id] = -float('inf')
                token_id += 1

            # if all logits are -inf, it means the model cannot generate a
            # valid token based on the constraints. In this case, we inject
            # a token that represents "none" to indicate that no valid
            # function name could be generated. We then append this token
            # to both the input_ids and generated lists, and set the
            # next_token to the token representing the closing brace of the
            # JSON object. If there are valid logits, we select the token
            # with the highest probability (argmax) as the next
            # token to generate.
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
            generated_str = model._tokenizer.decode(
                generated, skip_special_tokens=True)
            if with_animation:
                print(TO_SAVED_POSITION, CLEAR_DOWN)

                render_progress_bar(i)

                get_msg_template("cyan")("LLM TOKEN   ", f"'{token_str}'")

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
class ConstrainedParameterGenerator(BaseModel):
    def generate(self, model: Small_LLM_Model, prompt: str,
                 function_name: str, registry: ToolRegistry,
                 with_animation: bool = True,
                 max_new_tokens: int = 200) -> Any:

        """
        Generates function parameters based on the given prompt and
        function name using the provided model and registry.

        Args:
            model (Small_LLM_Model): The language model used for generation.
            prompt (str): The user request for which the function parameters
                          need to be generated.
            function_name (str): The name of the function for which the
                                 parameters need to be generated.
            registry (ToolRegistry): The registry containing available
                                     functions and their details.
            with_animation (bool, optional): Whether to display progress
                                             animation. Defaults to True.
            max_new_tokens (int, optional): Maximum number of tokens to
                                            generate. Defaults to 200.

        Returns:
            Any: The generated function parameters.
        """

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

        generated_str = ""
        next_token = 0

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

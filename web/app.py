from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from llm_sdk import Small_LLM_Model
from src import ConstrainedFnGenerator, ConstrainedParGenerator, ToolRegistry
import json
from typing import Dict, Any
import math
import re


app = Flask(__name__)
CORS(app)


def fn_add_numbers(a: int, b: int) -> int:
    """ Adds two numbers and returns the result."""
    return a + b


def fn_greet(name: str) -> str:
    """ Greets a person with their name.
    Args:
        name (str): The name of the person to greet.
    Returns:
        str: A greeting message.
    """
    return f"Hello, {name}"


def fn_reverse_string(s: str) -> str:
    """ Reverses a given string.
    Args:
        s (str): The string to be reversed.
    Returns:
        str: The reversed string.
    """
    return s[::-1]


def fn_get_square_root(a: int) -> float:
    """ Calculates the square root of a given number.
    Args:
        a (int): The number to calculate the square root of.
    Returns:
        float: The square root of the number.
    """
    return math.sqrt(a)


def fn_substitute_string_with_regex(source_string: str,
                                    regex: str, replacement: str) -> str:
    """
    Substitutes parts of a string that match a given regex pattern with a
    replacement string.
    Args:
        source_string (str): The original string.
        regex (str): The regex pattern to match.
        replacement (str): The string to replace matches with.
    Returns:
        str: The modified string after substitution.
    """
    return re.sub(regex, replacement, source_string)


def call_right_implementation(data: Dict[str, Any]) -> Any:
    """ Calls the appropriate function based on the provided data.
    Args:
        data (Dict[str, Any]): A dictionary containing the function name
                                and parameters.
    Returns:
        Any: The result of the function call.
    """
    if data["name"] == "fn_add_numbers":
        return fn_add_numbers(**data["parameters"])
    elif data["name"] == "fn_greet":
        return fn_greet(**data["parameters"])
    elif data["name"] == "fn_reverse_string":
        return fn_reverse_string(**data["parameters"])
    elif data["name"] == "fn_get_square_root":
        return fn_get_square_root(**data["parameters"])
    elif data["name"] == "fn_substitute_string_with_regex":
        return fn_substitute_string_with_regex(**data["parameters"])
    else:
        return None


@app.route('/')
def index() -> Any:
    return render_template("index.html")


@app.route('/api/chat', methods=['POST'])
def generate_llm_response() -> Any:
    """
    Generates an LLM response based on the provided prompt.

    reads the function definitions from a JSON file, initializes
    the LLM model and tool registry, and then processes the prompt received
    in the POST request. It generates a response using constrained function
    and parameter generators, calls the appropriate implementation based on the
    generated response, and returns a JSON response containing the original
    prompt, LLM response, and the result of the function call.

    Returns:
        Any: The generated LLM response.
    """
    with open('data/input/functions_definition.json', 'r') as f:
        tools = json.loads(f.read())

    model = Small_LLM_Model()
    registry = ToolRegistry(tools=tools)

    fn_constrained_gen = ConstrainedFnGenerator()
    parm_constrained_gen = ConstrainedParGenerator()

    data = request.get_json()
    prompt = data.get('prompt')

    res: Dict[str, str] = {"prompt": prompt}

    res.update(fn_constrained_gen.generate(model, prompt, registry, False))
    if (res["name"] == "none"):
        res["parameters"] = "none"
    else:
        res.update(parm_constrained_gen.generate(
            model, prompt, res["name"], registry, False))

    call_result = call_right_implementation(res)
    res["prompt"] = prompt
    response: Dict = {}
    response["request_type"] = "function_call"
    if (res["name"] == "none"):
        response["request_type"] = "Unknown"
    response["llm_response"] = res
    response["fncall_result"] = {"value": call_result, "status": "success"}
    if not call_result:
        response["fncall_result"] = {"value": "", "status": "failed"}
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)

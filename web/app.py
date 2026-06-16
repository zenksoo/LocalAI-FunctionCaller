from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from llm_sdk import Small_LLM_Model
from src.__main__ import ConstrainedGenerator, ToolRegistry
import json
from typing import Dict, Any
import math
import re


app = Flask(__name__)
CORS(app)


def fn_add_numbers(a: int, b: int) -> int:
    return a + b


def fn_greet(name: str) -> str:
    return f"Hello, {name}"


def fn_reverse_string(s: str) -> str:
    return s[::-1]


def fn_get_square_root(a: int) -> float:
    return math.sqrt(a)


def fn_substitute_string_with_regex(
    source_string: str, regex: str, replacement: str
    ) -> str:
    return re.sub(regex, replacement, source_string)


def call_right_implementation(data: Dict[str, Any]) -> Any:
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
def index():
    return render_template("index.html")


@app.route('/api/chat', methods=['POST'])
def test():
    with open('data/input/functions_definition.json', 'r') as f:
        tools = json.loads(f.read())
    model = Small_LLM_Model()
    registry = ToolRegistry(tools=tools)
    constrained_gen = ConstrainedGenerator()
    data = request.get_json()
    prompt = data.get('prompt')
    res = constrained_gen.generate(model, prompt, registry, False)
    result = call_right_implementation(res)
    if result:
        res["result"] = result
    return jsonify(res)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)

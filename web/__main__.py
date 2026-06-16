from flask import Flask, render_template, request, jsonify
from web.functions_implementations import call_right_implementation
from flask_cors import CORS
from llm_sdk import Small_LLM_Model
from src.__main__ import ConstrainedGenerator, ToolRegistry
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/api/test', methods = ['GET'])
def serv():
    return '<h1>HELLO SEL</h1>'

@app.route('/api/chat', methods = ['POST'])
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

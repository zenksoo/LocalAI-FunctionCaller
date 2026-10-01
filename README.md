*This project has been created as part of the 42 curriculum by amissa*

# Call Me Maybe

## Description

Call Me Maybe converts natural-language requests into structured function calls
using Qwen/Qwen3-0.6B and the supplied `llm_sdk` package. Instead of answering
“What is the sum of 2 and 3?”, it selects a tool such as `fn_add_numbers` and
extracts its arguments as JSON.

The program reads function definitions and prompts from JSON files, constrains
the model against those definitions, and writes one result per prompt. Function
names and parameter names are selected from the runtime input, so the solution is
not hardcoded to the example data.

## Requirements

- Python 3.10 or later
- `uv`
- The local model and dependencies provided through `LLM_SDK/`

The implementation uses Pydantic for validation and NumPy for logits masking and
selection.

## Instructions

Install `uv` if necessary:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install dependencies and run the default dataset:

```bash
make install
make run
```

Equivalent command:

```bash
uv run python3 -m src
```

Default paths:

- Functions: `data/input/functions_definition.json`
- Prompts: `data/input/function_calling_tests.json`
- Results: `data/output/function_calling_results.json`

Other targets:

```bash
make debug   # Run through pdb
make lint    # Run flake8 and mypy with the subject flags
make clean   # Remove Python and mypy caches
make web     # Run the optional Flask interface
```

## Example Usage

Run with custom files:

```bash
uv run python3 -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calls.json
```

Prompt input:

```json
[
  {"prompt": "What is the sum of 2 and 3?"},
  {"prompt": "Reverse the string 'hello'"}
]
```

Function definition input:

```json
[
  {
    "name": "fn_add_numbers",
    "description": "Add two numbers together and return their sum.",
    "parameters": {
      "a": {"type": "number"},
      "b": {"type": "number"}
    },
    "returns": {"type": "number"}
  }
]
```

Output:

```json
[
  {
    "prompt": "What is the sum of 2 and 3?",
    "name": "fn_add_numbers",
    "parameters": {"a": 2.0, "b": 3.0}
  }
]
```

Unknown requests are recorded with the current implementation's `none`
function name and `none` parameters.

## Algorithm Explanation

### Input validation

`GenerationConfig.load()` parses CLI options, loads both JSON files, and
validates records with Pydantic. `TestCaseSchema` requires a non-empty prompt;
`FunctionDefSchema` validates each function name, description, parameter map, and
return type. `ToolRegistry` exposes the valid names and parameter names to the
generators.

### Function-name constrained decoding

`ConstrainedFunctionNameGenerator` builds a prompt from the request and the
available function descriptions. It starts generation after the injected prefix:

```text
{"name": "
```

At each step, the model returns logits for the next token. NumPy stores the
logits as an array, and the generator decodes candidate vocabulary tokens to
check whether the accumulated text is a prefix of a registered function name or
`none`. Invalid entries are set to negative infinity, then `np.argmax` selects
the best remaining token. This makes an invalid function name impossible to
choose while still allowing the language model to select the function.

When a complete valid name is reached, the closing JSON text is injected into the
context. Fixed punctuation is not generated needlessly, and the resulting text is
parsed with `json.loads`.

### Parameter constrained decoding

`ConstrainedParameterGenerator` is a separate second stage. It receives the
original request, selected function, and parameter schema, then starts after:

```text
{"parameters": {"
```

While a parameter name is being generated, the same prefix constraint keeps only
tokens that can complete one of the selected function's remaining parameters.
After a name is complete, the separator `": ` is injected and the model extracts
its value. Known commas, quotes, and closing braces are injected as well. The
parameter prompt also instructs the model to preserve source values, follow JSON
types, use symbols literally, format regular expressions, and write numbers as
floating-point values when required.

Separating function selection from parameter extraction gives each stage a small,
clear state machine. Injected tokens keep the JSON structure deterministic while
the model focuses on semantic choices.

## Design Decisions

- **Runtime registry:** Function names, descriptions, and parameters come from
  the input files, supporting changing evaluator data.
- **Two generation stages:** Name selection and argument extraction have
  different constraints and are easier to inspect independently.
- **NumPy logits processing:** Arrays allow invalid logits to be masked with
  negative infinity and valid candidates to be selected efficiently with
  `np.argmax`, avoiding unconstrained generation followed by repair attempts.
- **Injected tokens:** Known JSON prefixes, separators, and closing delimiters are
  inserted directly into the context, reducing unnecessary model tokens.
- **Pydantic validation:** Bad external data fails early with structured errors.
- **Deterministic selection:** Argmax after masking is repeatable for a fixed
  model state and prompt.
- **Separate rendering module:** Progress, token traces, status, and errors do
  not clutter the generation logic.

## Performance Analysis

Compared with asking the model for complete JSON and retrying invalid answers,
this implementation avoids many invalid branches before token selection. NumPy
handles the logits array, function names and parameter names are constrained
separately, and injected JSON tokens remove predictable generation work. These
choices improve reliability and can reduce wasted generation compared with
unconstrained prompting.

Each remaining token still requires a model call and vocabulary inspection, so
runtime depends on vocabulary size, prompt count, maximum token count, and
hardware. Each stage currently allows up to 200 generated steps. The project does
not batch prompts or cache logits, so no unmeasured speed claim is made.

Reliability is strongest for JSON parsing and membership of function and
parameter names because invalid prefixes are masked. Parameter-value accuracy is
still model-dependent because values are extracted through the model prompt. The
included examples are a smoke test; an accuracy percentage should be measured
with a representative evaluator dataset.

## Challenges Faced

- **Small-model structured output:** A small model may produce invalid JSON or
  invent a function name. Prefix masking constrains the selectable names.
- **Subword token boundaries:** Names can span multiple tokens, so the algorithm
  checks accumulated decoded prefixes rather than assuming one token is one name.
- **JSON structure:** Quotes, commas, and braces are predictable; injecting them
  keeps the model from breaking the output format.
- **Runtime failures:** Missing files, invalid JSON, Pydantic errors, permission
  failures, and unexpected exceptions are handled by type-specific renderers and
  top-level exception handling.
- **Debugging generation:** Terminal visualization exposes each stage, selected
  token, injected text, partial response, progress, and prompt status.

## Bonus Features

The project includes these bonus-oriented features:

- **Advanced error handling:** `rendering.py` uses `singledispatch` for Pydantic
  validation errors, invalid JSON, missing files, permission errors, and generic
  failures. The entry point also handles prompt-level and application-level
  exceptions.
- **Generation visualization:** The terminal renders paths, prompt progress,
  stage labels, progress bars, selected tokens, injected text, intermediate JSON,
  final results, and passed/failed prompt markers.
- **Tokenizer-aware constraints:** Candidate tokens are decoded while masking,
  so constraints work across subword boundaries.
- **Optional web target:** The Makefile can launch the Flask interface in `web/`.

The current generator accesses the SDK tokenizer through `model._tokenizer` to
inspect individual tokens. The subject forbids private SDK attributes, so this
should be replaced with a public tokenizer adapter before submission if the SDK
provides one. Parameter names are explicitly constrained; full primitive-type
masking for parameter values would be a further improvement.

## Resources and AI Usage

- function calling concept: [hugginface docs](https://huggingface.co/docs/hugs/en/guides/function-calling) | [article on martinfowler](https://martinfowler.com/articles/function-call-LLM.html)

- constrained decoding: [article](https://zeroentropy.dev/concepts/constrained-decoding/)

- JSON: [python-json](https://realpython.com/python-json/)
- Python `argparse` documentation: <https://docs.python.org/3/library/argparse.html>
- Pydantic documentation: <https://docs.pydantic.dev/>
- NumPy documentation: <https://numpy.org/doc/>
- `uv` documentation: <https://docs.astral.sh/uv/>

AI assistance was used to review the subject requirements, organize this
README, and explain the existing implementation.

## Project Layout

```text
.
├── data/input/             Example prompts and function definitions
├── LLM_SDK/                Local SDK package and model metadata
├── src/
│   ├── __main__.py         CLI entry point and orchestration
│   ├── generation_core.py  Schemas, registry, and constrained generators
│   └── rendering.py        Errors, progress, and terminal visualization
├── web/                    Optional Flask interface
├── Makefile                Install, run, debug, lint, clean, and web targets
├── pyproject.toml          Project metadata and dependencies
└── README.md               Project documentation
```

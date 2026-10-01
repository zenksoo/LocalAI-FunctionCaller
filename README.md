*This project has been created as part of the 42 curriculum by amissa*

# Call Me Maybe

## Description

Call Me Maybe is a Python implementation of function calling for small language
models. It receives natural-language prompts and a JSON list of available tools,
then asks the Qwen/Qwen3-0.6B model to produce a structured function name and
typed arguments instead of a conversational answer.

The project follows the subject's central idea: constrained decoding makes the
model choose from values allowed by the supplied function definitions. The
implementation is organized into two generation steps:

1. Select the best function name, or `none` when no description matches.
2. Extract the parameters for the selected function.

The repository includes the supplied `llm_sdk` package under `LLM_SDK/`, input
examples under `data/input/`, and the implementation under `src/`.

## Requirements

- Python 3.10 or later
- `uv`
- A local model environment supported by the supplied `llm_sdk`

The project uses Pydantic for input/configuration models and NumPy for logits
processing. The model dependency is provided through the local `LLM_SDK` package.

## Instructions

Install `uv` if it is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install the locked project dependencies:

```bash
make install
```

Run the default example:

```bash
make run
```

The equivalent command is:

```bash
uv run python3 -m src
```

By default, the program reads:

- `data/input/functions_definition.json`
- `data/input/function_calling_tests.json`

and writes:

- `data/output/function_calling_results.json`

Custom paths can be supplied with the CLI options:

```bash
uv run python3 -m src \
	--functions_definition data/input/functions_definition.json \
	--input data/input/function_calling_tests.json \
	--output data/output/function_calls.json
```

Other Make targets are available:

```bash
make debug   # Run through pdb
make lint    # Run flake8 and mypy with the subject flags
make clean   # Remove Python and mypy caches
```

## Input Format

The prompt file is a JSON array of objects containing a non-empty `prompt`:

```json
[
	{"prompt": "What is the sum of 2 and 3?"},
	{"prompt": "Reverse the string 'hello'"}
]
```

The function definition file is a JSON array. Each function has a name,
description, parameter definitions, and return type:

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

Malformed JSON, missing files, invalid prompt records, and Pydantic validation
errors are routed through the formatted error handler in `src/rendering.py`.

## Output Format

For a successful prompt, the program writes an object containing the original
prompt, the selected function name, and the generated parameters:

```json
[
	{
		"prompt": "What is the sum of 2 and 3?",
		"name": "fn_add_numbers",
		"parameters": {
			"a": 2.0,
			"b": 3.0
		}
	}
]
```

When no available function matches, the current implementation records the
function name as `none` and the parameters value as `none`.

## Algorithm

### Configuration and validation

`GenerationConfig.load()` parses command-line arguments, loads both JSON input
files, and validates prompt records with `TestCaseSchema` and function records
with `FunctionDefSchema`. `ToolRegistry` stores the validated tool definitions
and builds the prompts used by the model.

### Constrained function-name generation

`ConstrainedFunctionNameGenerator` constructs a prompt containing the user
request and the available function descriptions. It then starts generation after
the JSON prefix `{"name": "`.

At each token step, the generator decodes candidate vocabulary tokens and keeps a
token only when the accumulated text is a prefix of at least one valid function
name or of `none`. All other logits are set to negative infinity. The highest
remaining logit is selected with argmax. Once a complete valid name is reached,
the closing JSON text is injected and generation stops.

This prefix filtering prevents the model from producing a function name that is
not present in the supplied tool registry while still allowing the model to
choose between the available descriptions.

### Constrained parameter generation

`ConstrainedParameterGenerator` builds a second prompt containing the selected
function description and its parameter schema. The generator starts after the
JSON prefix for the `parameters` object.

The parameter-name state uses the same prefix filtering approach: only tokens
that can complete one of the selected function's parameter names remain valid.
When a parameter name is complete, the parameter separator is injected and the
model generates its value. Parameter names are removed from the remaining set,
and closing braces or separators are injected as needed. The prompt explicitly
asks the model to preserve source values, respect JSON types, use symbols rather
than symbol names, and represent numeric integers as floating-point values.

The final generated text is parsed with `json.loads`, so malformed generated JSON
raises an error instead of silently producing an invalid result.

## Design Decisions

- `ToolRegistry` keeps tool discovery and prompt construction separate from the
	generation loops.
- Pydantic models validate the external JSON structure before model execution.
- Function selection and parameter extraction are separate stages, which makes
	each constraint state small and inspectable.
- Argmax is used after masking invalid tokens, giving deterministic output for a
	fixed model and prompt.
- Terminal output is isolated in `rendering.py`, including progress bars,
	per-prompt status, and type-specific error messages.
- `data/output/` is created on demand by `GenerationConfig.write_results()`.

## Performance and Reliability

Each generated token requires a call to `get_logits_from_input_ids`. The current
implementation favors explicit token-by-token constraints and clarity over
batching or caching. Runtime therefore depends on the number of prompts, the
maximum token count, and the local model hardware.

Reliability is strongest for JSON structure and valid function/parameter names:
invalid name prefixes are masked before token selection, and the completed text
is parsed as JSON. Semantic accuracy of values still depends on the model and the
quality of the natural-language prompt. The repository does not currently include
an automated accuracy benchmark, so accuracy and runtime should be measured with
the evaluator's prompt set.

## Testing Strategy

The included input set covers addition, greetings, string reversal, square roots,
regex replacement, multiple parameters, and quoted values. A practical manual
check is:

```bash
make install
make lint
make run
python3 -m json.tool data/output/function_calling_results.json
```

For additional checks, replace the files passed to `--input` and
`--functions_definition` with cases containing empty strings, large numbers,
special characters, multiple parameters, ambiguous descriptions, malformed JSON,
and missing files. Confirm that successful output is parseable JSON and that every
generated function name and parameter name comes from the supplied definitions.

## Known Implementation Notes

The current generator accesses the SDK tokenizer through `model._tokenizer` so it
can inspect individual token strings during masking. The subject identifies SDK
private attributes as forbidden; this should be refactored to a public tokenizer
adapter before submission if the SDK exposes or permits one.

The current parameter constraint controls parameter names and delegates value
generation to the model prompt. A stricter implementation would additionally
mask tokens according to each parameter's declared primitive type while values
are being generated.

## Resources and AI Usage

Relevant resources:

- The provided `en.subject.pdf`, especially the sections on function calling,
	constrained decoding, JSON schemas, and the `llm_sdk` interface.
- Python `json` documentation: <https://docs.python.org/3/library/json.html>
- Python `argparse` documentation: <https://docs.python.org/3/library/argparse.html>
- Pydantic documentation: <https://docs.pydantic.dev/>
- NumPy documentation: <https://numpy.org/doc/>
- `uv` documentation: <https://docs.astral.sh/uv/>

AI assistance was used to organize and review project documentation, summarize
the subject requirements, and explain the existing source structure.

## Project Layout

```text
.
├── data/input/             Example prompts and function definitions
├── LLM_SDK/                Local SDK package and model dependency metadata
├── src/
│   ├── __main__.py         CLI entry point and generation orchestration
│   ├── generation_core.py  Schemas, registry, and constrained generators
│   └── rendering.py        Terminal progress and error rendering
├── Makefile                Install, run, debug, lint, clean, and web targets
├── pyproject.toml          Project metadata and dependencies
└── README.md               Project documentation
```

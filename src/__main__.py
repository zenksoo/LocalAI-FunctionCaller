from src.generation_core import (GenerationConfig, ToolRegistry,
                                 ConstrainedFunctionNameGenerator,
                                 ConstrainedParameterGenerator)
from src.rendering import (get_error_handler, get_msg_template,
                           render_prompts_stat)
from typing import List, Dict, Any
from llm_sdk import Small_LLM_Model
import sys
import time


RESET_TERMINAL = "\033[H\033[J"


def render_configuration(config: GenerationConfig) -> None:
    """
    Renders the configuration information.

    Args:
        config (Config): The configuration object
                       containing paths and settings.
    """
    get_msg_template("white")(
                "PATHS              ", "")
    get_msg_template("magenta")(
                "FUNCTION DEFINITION", f"'{config.fn_definition_path}'")
    get_msg_template("magenta")(
                "USER PROMPTS       ", f"'{config.input_path}'")
    get_msg_template("magenta")(
                "OUTPUT PATH        ", f"'{config.output_path}'")


if __name__ == "__main__":
    """
        Main entry point of the program. It initializes the configuration,
        model, and generators, and processes each prompt to generate
        function names and parameters. The results are saved to the
        specified output path.
    """

    render_exception = get_error_handler()
    constrained_fn_gen = ConstrainedFunctionNameGenerator()
    constrained_parm_gen = ConstrainedParameterGenerator()

    try:
        config = GenerationConfig.load()
        registry = ToolRegistry(tools=config.tools)

        model = Small_LLM_Model()

        results: List[Dict[str, Any]] = []
        passed_prompts: List[bool] = []

        start = time.perf_counter()
        for prompt in config.prompts:
            response: Dict[str, str] = {}

            print(RESET_TERMINAL)

            render_configuration(config)
            render_prompts_stat(config.prompts, passed_prompts)
            get_msg_template("green")("PROMPT", prompt)

            try:
                response["prompt"] = prompt
                response.update(
                    constrained_fn_gen.generate(model, prompt, registry))
                if response["name"] == "none":
                    response["parameters"] = "none"
                else:
                    response.update(
                        constrained_parm_gen.generate(
                            model, prompt, response["name"], registry))
                passed_prompts.append(True)
                results.append(response)
            except KeyboardInterrupt:
                passed_prompts.append(False)

        print(RESET_TERMINAL)
        render_configuration(config)
        render_prompts_stat(config.prompts, passed_prompts)

        end = time.perf_counter()
        exuction_time = (end - start) / 60
        with open("excution_time.txt", 'a') as f:
            f.write(f"{exuction_time:.6f}\n")
        try:
            config.write_results(results)
            get_msg_template("green")(
                "[+] All DONE and SAVED", "")

        except (PermissionError, IOError) as e:
            render_exception(e)

    except SystemExit:
        pass
    except (BaseException, KeyboardInterrupt) as e:
        render_exception(e)
        sys.exit(1)
    sys.exit(0)

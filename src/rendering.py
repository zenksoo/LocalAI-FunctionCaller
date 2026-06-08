from json.decoder import JSONDecodeError
from pydantic import ValidationError
from functools import singledispatch
from typing import List, Callable
from sys import stderr
import sys


# Reset
RESET = "\033[0m"

# Foreground colors
FG_BLACK = "\033[30m"
FG_RED = "\033[31m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_BLUE = "\033[34m"
FG_MAGENTA = "\033[35m"
FG_CYAN = "\033[36m"
FG_WHITE = "\033[37m"
FG_DEFAULT = "\033[39m"

# Background colors
BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"
BG_WHITE = "\033[47m"
BG_DEFAULT = "\033[49m"

# symbols
ARROW = "→"
OK = "✔"
FAIL = "✘"


def get_error_handler() -> Callable[[BaseException], None]:
    @singledispatch
    def _handle_by_type(error_type: BaseException) -> None:
        print(f"{BG_BLUE} {RESET} {error_type}")

    @_handle_by_type.register(ValidationError)
    def _(exc: ValidationError) -> None:
        for error in exc.errors():
            if error["type"] == "missing":
                print(f"{BG_BLUE} {RESET} Missing",
                      "Required Field:",
                      f"{', '.join([e for e in error["loc"]])}")
            else:
                print(f"{BG_BLUE} {RESET} {error["msg"]}")

    @_handle_by_type.register(JSONDecodeError)
    def _(exc: JSONDecodeError) -> None:
        print(f"{BG_BLUE} {RESET} Invalid",
              f"Formate For JSON File: {exc}\n", file=stderr)

    @_handle_by_type.register(PermissionError)
    def _(exc: PermissionError) -> None:
        print(f"{BG_BLUE} {RESET} Permission Denied: {exc.filename}")

    @_handle_by_type.register(FileNotFoundError)
    def _(exc: FileNotFoundError) -> None:
        print(f"{BG_BLUE} {RESET} File not found: {exc.filename}")

    def render_exception(error: BaseException) -> None:
        print(f"\n{BG_RED}{FG_BLACK}   Program Failed !!",
              f"  {RESET}", file=stderr, end="")
        print(f"{BG_YELLOW}{FG_BLACK} Error Type:",
              f"{error.__class__.__name__} {RESET}")
        _handle_by_type(error)
        print()

    return render_exception


def render_progress_bar(i: int, items: int = 200,
                        bar_length: int = 50) -> None:
    sys.stdout.write("\033[?25l")

    percent = (i / items) * 100

    filled_length = int(bar_length * i // items)

    bar = '█' * filled_length + '░' * (bar_length - filled_length)

    output = f"\r|{bar}| {percent:>5.1f}% ({i}/{items})"

    sys.stdout.write(output + "\033[K")
    sys.stdout.flush()


def render_prompts_stat(prompts: List[str],
                        passed_prompt: List[bool]) -> None:
    print("PASSED PROMPTS [ ", end="")
    for e in passed_prompt:
        if e:
            print(f"{FG_GREEN} {OK} {RESET}", end="")
        else:
            print(f"{FG_RED} {FAIL} {RESET}", end="")
    print(" - " * (len(prompts) - len(passed_prompt)), end="")
    print(" ]")


def get_msg_template(color: str) -> Callable:
    def cyan_msg_bar(title: str, msg: str) -> None:
        print(f"\n\n{BG_CYAN}{FG_BLACK}  {title}  {BG_DEFAULT}   {msg}")

    def yellow_msg_bar(title: str, msg: str) -> None:
        print(f"\n{BG_YELLOW}{FG_BLACK}  {title}   {RESET}   {msg}")

    def green_msg_bar(title: str, msg: str) -> None:
        print(f"\n{BG_GREEN}{FG_GREEN}  {title}  {RESET}   {msg}")

    if color == "cyan":
        return cyan_msg_bar
    elif color == "yellow":
        return yellow_msg_bar
    elif color == "green":
        return green_msg_bar
    else:
        raise ValueError(f"Unregistred Color Name '{color}'!!")

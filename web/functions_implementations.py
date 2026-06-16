from typing import List, Dict, Any
import math

def fn_add_numbers(a: int, b: int) -> int:
    return a + b


def fn_greet(name: str) -> str:
    return f"Hello, {name}"


def fn_reverse_string(s: str) -> str:
    return s[::-1]


def fn_get_square_root(a: int) -> int:
    return math.sqrt(a)


def call_right_implementation(data: Dict[str, Any]) -> Any:
    if data["name"] == "fn_add_numbers":
        return fn_add_numbers(**data["parameters"])
    elif data["name"] == "fn_greet":
       return fn_greet(**data["parameters"])
    elif data["name"] == "fn_reverse_string":
        return fn_reverse_string(**data["parameters"])
    elif data["name"] == "fn_get_square_root":
        return fn_get_square_root(**data["parameters"])
    else:
        return None




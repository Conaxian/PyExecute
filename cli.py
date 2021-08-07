import sys
from json import dumps
from pyexecute import PyExecutor, ExecTimeoutError, UnsafeCodeError

class ArgCountError(Exception):
    """
    Thrown when there are too few or too many arguments.
    """

def safe_index(list: list, index: int):
    """
    Returns the list element at index.
    If the index is invalid, returns None instead.
    """
    try:
        return list[index]
    except IndexError:
        return None

def safe_float(string: str) -> float:
    """
    Converts the string to a float.
    If the conversion fails, return None instead.
    """
    try:
        return float(string)
    except (TypeError, ValueError):
        return None

def safe_int(string: str) -> int:
    """
    Converts the string to an integer.
    If the conversion fails, return None instead.
    """
    try:
        return int(string)
    except (TypeError, ValueError):
        return None

args = {}

args["filename"] = safe_index(sys.argv, 1)
if not args["filename"]: raise ArgCountError

args["timeout"] = safe_float(safe_index(sys.argv, 2)) or 5
args["checks_per_second"] = safe_int(safe_index(sys.argv, 3)) or 40
args["python_cmd"] = safe_index(sys.argv, 4)
if safe_index(sys.argv, 5): raise ArgCountError

with open(args["filename"], "r") as file:
    code = file.read()

executor = PyExecutor(**args)
try:
    result = executor.execute(code)
    json = dumps({
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exec_time": result.exec_time
    })
    print(json)
except ExecTimeoutError:
    print("ExecTimeoutError", file=sys.stderr)
except UnsafeCodeError:
    print("UnsafeCodeError", file=sys.stderr)

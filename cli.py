import os
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

def safe_int(string: str) -> int:
    """
    Converts the string to an integer.
    If the conversion fails, returns None instead.
    """
    try:
        return int(string)
    except (TypeError, ValueError):
        return None

def safe_float(string: str) -> float:
    """
    Converts the string to a float.
    If the conversion fails, returns None instead.
    """
    try:
        return float(string)
    except (TypeError, ValueError):
        return None

args = {}
scan = False

args["filename"] = safe_index(sys.argv, 1)
if not args["filename"]: raise ArgCountError
args["filename"] = os.path.abspath(args["filename"])

scan = safe_index(sys.argv, 2) != "False"

args["timeout"] = safe_float(safe_index(sys.argv, 3)) or 5
args["checks_per_second"] = safe_int(safe_index(sys.argv, 4)) or 40
args["python_cmd"] = safe_index(sys.argv, 5)

if safe_index(sys.argv, 6): raise ArgCountError

with open(args["filename"], "r", encoding="utf-8") as file:
    code = file.read()

executor = PyExecutor(**args)
try:
    result = executor.execute(code, scan)
    json = dumps({
        "stdout": result.stdout,
        "stderr": result.stderr,
        "execTime": result.exec_time
    })
    print(json)
except UnsafeCodeError as err:
    print(f"UnsafeCodeError: {err.args[0]}", file=sys.stderr)
except ExecTimeoutError:
    print("ExecTimeoutError", file=sys.stderr)

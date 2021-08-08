import os
import time
import ast
import traceback
import subprocess
import signal
import locale
from typing import Union

ALLOWED_MODULES = [
    "datetime",
    "math",
    "random",
    "hashlib",
    "time",
    "getpass",
    "socket",
    "urllib"
]
BANNED_NAMES = [
    "exec",
    "eval",
    "compile",
    "globals",
    "locals",
    "vars",
    "builtins",
    "dir",
    "open",
    "input",
    "breakpoint",
    "getattr",
    "delattr",
    "__dict__",
    "__base__"
]

class ExecTimeoutError(Exception):
    """
    Raised when the execution times out.
    """

class UnsafeCodeError(Exception):
    """
    Raised when the passed code is unsafe.
    """

class Result:
    """
    Represents an execution result.
    """

    def __init__(self, stdout: str, stderr: str, exec_time: int):
        self.stdout = stdout
        self.stderr = stderr
        self.exec_time = exec_time

class PyExecutor:

    def __init__(self,
        filename: str,
        timeout: Union[int, float]=5,
        checks_per_second: int=40,
        python_cmd: str=None
    ):
        self.filename = filename
        self.timeout = timeout
        self.check_interval = 1 / checks_per_second

        current_dir = os.path.dirname(__file__)
        current_path = os.path.abspath(current_dir)
        self.file_path = os.path.join(current_path, filename)
        self.win = os.name == "nt"
        self.python_cmd = python_cmd or \
            ("python" if self.win else "python3")

    def execute(self, code: str, scan: bool=True) -> Result:
        """
        Safely executes Python code.
        """
        code = code.strip(" \t\n")
        task = _Task(self, code)

        if scan:
            try:
                self.scan(code)
            except SyntaxError:
                error = traceback.format_exc(limit=0)
                return Result("", error, 0)

        task.run()
        limit = time.time() + self.timeout

        while time.time() < limit:
            time.sleep(self.check_interval)
            if not task.is_running():
                result = task.process.communicate()
                encoding = locale.getpreferredencoding()
                stdout, stderr = (bytestr.decode(encoding).strip() \
                    for bytestr in result)
                exec_time = time.time() - task.exec_start
                return Result(stdout, stderr, exec_time)

        task.kill()
        raise ExecTimeoutError(time.time() - task.exec_start)

    @staticmethod
    def scan(code: str):
        """
        Scans the passed code and determines
        whether it's safe or not.
        """
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and \
                node.id in BANNED_NAMES:
                raise UnsafeCodeError(node.id)

            if isinstance(node, ast.Attribute) and \
                node.attr in BANNED_NAMES:
                raise UnsafeCodeError(node.attr)

            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in ALLOWED_MODULES:
                        raise UnsafeCodeError(alias.name)

            if isinstance(node, ast.ImportFrom) and \
                node.module not in ALLOWED_MODULES:
                raise UnsafeCodeError(node.module)

class _Task:
    """
    Represents a single code execution task.
    This class should only be instantiated using an executor.
    """

    def __init__(self, executor: PyExecutor, code: str):
        self.executor = executor
        self.code = code

    def is_running(self) -> bool:
        """
        Checks if the task is still running.
        """
        if self.executor.win:
            tasklist_cmd = f'tasklist /FI "pid eq {self.pid}"'
            tasklist_cond = "INFO: No tasks are running"
        else:
            tasklist_cmd = f"ps -p {self.pid}"
            tasklist_cond = "<defunct>"
        tasklist = os.popen(tasklist_cmd).read()
        return tasklist_cond not in tasklist

    def run(self):
        """
        Runs the task.
        """
        self.exec_start = time.time()
        with open(self.executor.file_path, "w",
            encoding="utf-8") as file:
            file.write(self.code)

        popen_args = [
            self.executor.python_cmd,
            self.executor.file_path,
        ]
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE
        }
        if self.executor.win:
            popen_kwargs["creationflags"] = \
                subprocess.CREATE_NEW_PROCESS_GROUP | \
                subprocess.CREATE_NO_WINDOW

        self.process = subprocess.Popen(popen_args, **popen_kwargs)
        self.pid = self.process.pid

    def kill(self):
        """
        Kills the task.
        """
        kill_command = ["taskkill", "/F", "/PID"] \
            if self.executor.win else ["kill", "-" + str(signal.SIGKILL)]
        kill_command.append(str(self.pid))
        subprocess.check_call(kill_command, stdout=subprocess.DEVNULL)

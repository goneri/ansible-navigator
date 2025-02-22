"""Herewithin lies the base class for running commands
using ansible-runner. All attributes common to a
subprocess or async command are defined here
"""
import sys

from typing import List
from typing import Optional

from ..utils.functions import shlex_join
from .base import Base


class CommandBase(Base):
    # pylint: disable=too-many-arguments

    """Base class for runner command interaction"""

    def __init__(
        self,
        executable_cmd: str,
        cmdline: Optional[List] = None,
        playbook: Optional[str] = None,
        inventory: Optional[List] = None,
        wrap_sh: Optional[bool] = False,
        **kwargs,
    ):
        """Base class to handle common arguments of ``run_command`` interface for ``ansible-runner``
        Args:
            executable_cmd ([str]): The command to be invoked.
            cmdline ([list], optional): A list of arguments to be passed to the executable command.
                                        Defaults to None.
            playbook ([str], optional): The playbook file name to run. Defaults to None.
            inventory ([list], optional): List of path to the inventory files. Defaults to None.
            wrap_sh ([bool], optional): Wrap the command with `sh -c`, disregarding stderr output.
                                        Runner will pass --tty in almost all (default) cases. When
                                        that flag is given, docker and podman will combine the
                                        process's stdout and stderr into just stdout. Wrapping the
                                        command with sh allows us to disregard the stderr output
                                        when we only care about stdout.
        """
        self._executable_cmd = executable_cmd
        self._cmdline: List[str] = cmdline if isinstance(cmdline, list) else []
        self._playbook = playbook
        self._inventory: List[str] = inventory if isinstance(inventory, list) else []
        self._wrap_sh = wrap_sh
        super().__init__(**kwargs)

    def generate_run_command_args(self) -> None:
        """Generate arguments required to be passed to ansible-runner."""
        if self._playbook:
            self._cmdline.insert(0, self._playbook)

        for inv in self._inventory:
            self._cmdline.extend(["-i", inv])

        if self._wrap_sh:
            self._cmdline.insert(0, self._executable_cmd)
            self._runner_args["executable_cmd"] = "/bin/sh"
            cmd_args = shlex_join(self._cmdline)
            self._runner_args["cmdline_args"] = ["-c", f"exec 2>/dev/null; {cmd_args}"]
        else:
            self._runner_args["executable_cmd"] = self._executable_cmd
            self._runner_args["cmdline_args"] = self._cmdline

        if self._navigator_mode == "stdout":
            self._runner_args.update(
                {"input_fd": sys.stdin, "output_fd": sys.stdout, "error_fd": sys.stderr},
            )

        for key, value in self._runner_args.items():
            self._logger.debug("Runner arg: %s:%s", key, value)

"""
C program runner for pytest-cprobe.
"""

import subprocess
import signal
import os
import resource
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
import tempfile

if TYPE_CHECKING:
    from .sanitizers import SanitizerConfig


class RunnerError(Exception):
    """Raised when program execution fails."""
    pass


class CRunner:
    """Runner for compiled C programs."""

    def __init__(
        self,
        work_dir: Optional[Path] = None,
        timeout: Optional[float] = None,
        capture_core: bool = True
    ):
        self.work_dir = work_dir or Path(tempfile.mkdtemp())
        self.timeout = timeout
        self.capture_core = capture_core

        # Enable core dumps if requested
        if capture_core:
            self._enable_core_dumps()

    def _enable_core_dumps(self) -> None:
        """Enable core dump generation."""
        try:
            # Set unlimited core dump size
            resource.setrlimit(resource.RLIMIT_CORE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except (OSError, ValueError):
            # Some systems may not allow this
            pass

    def run(
        self,
        executable: Path,
        args: Optional[List[str]] = None,
        stdin_data: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        sanitizer_config: Optional['SanitizerConfig'] = None
    ) -> subprocess.CompletedProcess:
        """Run an executable and return the result."""
        if not executable.exists():
            raise RunnerError(f"Executable {executable} does not exist")

        if not executable.is_file():
            raise RunnerError(f"Path {executable} is not a file")

        # Make sure executable has execute permissions
        executable.chmod(0o755)

        cmd = [str(executable)]
        if args:
            cmd.extend(args)

        # Set up environment
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        # Add sanitizer environment variables
        if sanitizer_config:
            sanitizer_env = sanitizer_config.get_runtime_env()
            run_env.update(sanitizer_env)

        # Set core dump pattern to work directory if capturing cores
        if self.capture_core:
            run_env["PYTEST_CPROBE_WORK_DIR"] = str(self.work_dir)

        # Use provided timeout or instance timeout
        actual_timeout = timeout if timeout is not None else self.timeout

        try:
            result = subprocess.run(
                cmd,
                cwd=self.work_dir,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=actual_timeout,
                env=run_env
            )

            # Check for core dump
            if result.returncode < 0:
                # Process was terminated by signal
                signal_num = abs(result.returncode)
                result.signal_name = signal.Signals(signal_num).name if signal_num in signal.Signals._value2member_map_ else f"SIG{signal_num}"

                # Look for core dump
                core_file = self._find_core_dump(executable.name)
                if core_file:
                    result.core_file = core_file

            return result

        except subprocess.TimeoutExpired as e:
            raise RunnerError(f"Program execution timed out after {actual_timeout} seconds") from e
        except subprocess.SubprocessError as e:
            raise RunnerError(f"Failed to run program: {e}") from e

    def run_with_input_file(
        self,
        executable: Path,
        input_file: Path,
        args: Optional[List[str]] = None,
        **kwargs
    ) -> subprocess.CompletedProcess:
        """Run executable with input from a file."""
        if not input_file.exists():
            raise RunnerError(f"Input file {input_file} does not exist")

        stdin_data = input_file.read_text()
        return self.run(executable, args, stdin_data=stdin_data, **kwargs)

    def run_with_valgrind(
        self,
        executable: Path,
        args: Optional[List[str]] = None,
        valgrind_args: Optional[List[str]] = None,
        **kwargs
    ) -> subprocess.CompletedProcess:
        """Run executable under valgrind."""
        import shutil

        if not shutil.which("valgrind"):
            raise RunnerError("valgrind not found in PATH")

        valgrind_cmd = ["valgrind"]
        if valgrind_args:
            valgrind_cmd.extend(valgrind_args)
        else:
            # Default valgrind options
            valgrind_cmd.extend([
                "--tool=memcheck",
                "--leak-check=full",
                "--show-leak-kinds=all",
                "--track-origins=yes"
            ])

        valgrind_cmd.append(str(executable))
        if args:
            valgrind_cmd.extend(args)

        # Run valgrind command directly
        try:
            result = subprocess.run(
                valgrind_cmd,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=kwargs.get('timeout', self.timeout),
                env=kwargs.get('env')
            )

            return result

        except subprocess.SubprocessError as e:
            raise RunnerError(f"Failed to run valgrind: {e}") from e

    def _find_core_dump(self, program_name: str) -> Optional[Path]:
        """Find core dump file for a program."""
        # Common core dump patterns
        patterns = [
            f"core.{program_name}.*",
            "core.*",
            "core",
            f"{program_name}.core"
        ]

        for pattern in patterns:
            cores = list(self.work_dir.glob(pattern))
            if cores:
                # Return the most recent core dump
                return max(cores, key=lambda p: p.stat().st_mtime)

        return None

    def get_exit_code_meaning(self, returncode: int) -> str:
        """Get human-readable meaning of exit code."""
        if returncode == 0:
            return "Success"
        elif returncode > 0:
            return f"Error (exit code {returncode})"
        else:
            # Negative return code means killed by signal
            signal_num = abs(returncode)
            try:
                sig_name = signal.Signals(signal_num).name
                return f"Killed by signal {signal_num} ({sig_name})"
            except ValueError:
                return f"Killed by signal {signal_num}"

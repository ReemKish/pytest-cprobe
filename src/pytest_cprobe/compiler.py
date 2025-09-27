"""
C compiler wrapper for pytest-cprobe.
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile

from .sanitizers import SanitizerConfig


class CompilerError(Exception):
    """Raised when C compilation fails."""

    def __init__(self, message: str, stdout: str = "", stderr: str = "", returncode: int = 1):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class CCompiler:
    """Wrapper for C compilers like gcc and clang."""

    def __init__(
        self,
        compiler: str = "gcc",
        work_dir: Optional[Path] = None,
        debug: bool = False,
        sanitizer_config: Optional[SanitizerConfig] = None,
        extra_flags: Optional[List[str]] = None
    ):
        self.compiler = compiler
        self.work_dir = work_dir or Path(tempfile.mkdtemp())
        self.debug = debug
        self.sanitizer_config = sanitizer_config
        self.extra_flags = extra_flags or []

        # Verify compiler exists
        if not shutil.which(self.compiler):
            raise CompilerError(f"Compiler '{self.compiler}' not found in PATH")

    def _get_base_flags(self) -> List[str]:
        """Get base compilation flags."""
        flags = []

        if self.debug:
            flags.extend(["-g", "-O0"])
        else:
            flags.extend(["-O2"])

        # Add sanitizer flags
        if self.sanitizer_config:
            flags.extend(self.sanitizer_config.get_compile_flags())

        # Add extra flags
        flags.extend(self.extra_flags)

        return flags

    def compile_shared_lib(self, source_code: str, filename: str) -> Path:
        """Compile C source code to a shared library."""
        source_path = self.work_dir / filename
        lib_name = source_path.stem + ".so"
        lib_path = self.work_dir / lib_name

        # Write source code to file
        source_path.write_text(source_code)

        # Compile command
        cmd = [
            self.compiler,
            "-shared",
            "-fPIC",
            *self._get_base_flags(),
            "-o", str(lib_path),
            str(source_path)
        ]

        return self._run_compile_command(cmd, lib_path)

    def needs_sanitizer_preload(self) -> bool:
        """Check if sanitizer needs to be preloaded for shared libraries."""
        return self.sanitizer_config is not None and self.sanitizer_config.sanitizer_type.value in ['address', 'memory']

    def get_sanitizer_preload_lib(self) -> Optional[str]:
        """Get path to sanitizer library for LD_PRELOAD."""
        if not self.sanitizer_config:
            return None

        # Try to find the sanitizer library
        if self.sanitizer_config.sanitizer_type.value == 'address':
            # Common locations for libasan
            possible_paths = [
                "/usr/lib/x86_64-linux-gnu/libasan.so",
                "/usr/lib64/libasan.so",
                "/usr/lib/libasan.so",
            ]
        elif self.sanitizer_config.sanitizer_type.value == 'memory':
            possible_paths = [
                "/usr/lib/x86_64-linux-gnu/libmsan.so",
                "/usr/lib64/libmsan.so",
                "/usr/lib/libmsan.so",
            ]
        else:
            return None

        for path in possible_paths:
            if Path(path).exists():
                return path

        # Try to get from compiler
        try:
            result = subprocess.run(
                [self.compiler, f"-print-file-name=lib{self.sanitizer_config.sanitizer_type.value}san.so"],
                capture_output=True,
                text=True,
                check=True
            )
            lib_path = result.stdout.strip()
            if lib_path and Path(lib_path).exists():
                return lib_path
        except subprocess.SubprocessError:
            pass

        return None

    def compile_executable(self, source_code: str, filename: str) -> Path:
        """Compile C source code to an executable."""
        source_path = self.work_dir / filename
        exe_name = source_path.stem
        exe_path = self.work_dir / exe_name

        # Write source code to file
        source_path.write_text(source_code)

        # Compile command
        cmd = [
            self.compiler,
            *self._get_base_flags(),
            "-o", str(exe_path),
            str(source_path)
        ]

        return self._run_compile_command(cmd, exe_path)

    def compile_object(self, source_code: str, filename: str) -> Path:
        """Compile C source code to an object file."""
        source_path = self.work_dir / filename
        obj_name = source_path.stem + ".o"
        obj_path = self.work_dir / obj_name

        # Write source code to file
        source_path.write_text(source_code)

        # Compile command
        cmd = [
            self.compiler,
            "-c",
            *self._get_base_flags(),
            "-o", str(obj_path),
            str(source_path)
        ]

        return self._run_compile_command(cmd, obj_path)

    def link_executable(self, object_files: List[Path], output_name: str) -> Path:
        """Link object files into an executable."""
        exe_path = self.work_dir / output_name

        cmd = [
            self.compiler,
            *self._get_base_flags(),
            "-o", str(exe_path),
            *[str(obj) for obj in object_files]
        ]

        return self._run_compile_command(cmd, exe_path)

    def _run_compile_command(self, cmd: List[str], expected_output: Path) -> Path:
        """Run a compile command and handle errors."""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                raise CompilerError(
                    f"Compilation failed with return code {result.returncode}",
                    stdout=result.stdout,
                    stderr=result.stderr,
                    returncode=result.returncode
                )

            if not expected_output.exists():
                raise CompilerError(
                    f"Expected output file {expected_output} was not created",
                    stdout=result.stdout,
                    stderr=result.stderr
                )

            return expected_output

        except subprocess.SubprocessError as e:
            raise CompilerError(f"Failed to run compiler: {e}")

    def get_compiler_info(self) -> Dict[str, Any]:
        """Get information about the compiler."""
        try:
            result = subprocess.run(
                [self.compiler, "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            return {
                "compiler": self.compiler,
                "version_output": result.stdout,
                "available": True
            }
        except (subprocess.SubprocessError, FileNotFoundError):
            return {
                "compiler": self.compiler,
                "available": False
            }

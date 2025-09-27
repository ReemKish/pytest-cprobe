"""
Main pytest plugin module for pytest-cprobe.
"""

from typing import Generator, Optional, Dict, Any, List
import pytest
import tempfile
import os
import shutil
import subprocess
import ctypes
import signal
import sys
from pathlib import Path

from .compiler import CCompiler
from .runner import CRunner
from .sanitizers import SanitizerConfig
from .crash_analyzer import CrashAnalyzer


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options for pytest-cprobe."""
    group = parser.getgroup("cprobe", "C code testing with pytest-cprobe")

    group.addoption(
        "--cprobe-compiler",
        action="store",
        default="gcc",
        help="C compiler to use (default: gcc)",
    )

    group.addoption(
        "--cprobe-sanitizer",
        action="store",
        default=None,
        help="Sanitizer to enable (address, memory, thread, undefined)",
    )

    group.addoption(
        "--cprobe-debug",
        action="store_true",
        help="Enable debug symbols in compiled C code",
    )

    group.addoption(
        "--cprobe-keep-temps",
        action="store_true",
        help="Keep temporary files for debugging",
    )


@pytest.fixture(scope="function")
def cprobe_temp_dir(request: pytest.FixtureRequest) -> Generator[Path, None, None]:
    """Provide a temporary directory for C code compilation and execution."""
    temp_dir = Path(tempfile.mkdtemp(prefix="pytest_cprobe_"))

    try:
        yield temp_dir
    finally:
        if not request.config.getoption("--cprobe-keep-temps"):
            shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def c_compiler(request: pytest.FixtureRequest, cprobe_temp_dir: Path) -> CCompiler:
    """Provide a C compiler instance configured with options from command line."""
    compiler_name = request.config.getoption("--cprobe-compiler")
    debug = request.config.getoption("--cprobe-debug")
    sanitizer = request.config.getoption("--cprobe-sanitizer")

    sanitizer_config = None
    if sanitizer:
        sanitizer_config = SanitizerConfig(sanitizer)

    return CCompiler(
        compiler=compiler_name,
        work_dir=cprobe_temp_dir,
        debug=debug,
        sanitizer_config=sanitizer_config
    )


@pytest.fixture(scope="function")
def c_runner(cprobe_temp_dir: Path) -> CRunner:
    """Provide a C program runner."""
    return CRunner(work_dir=cprobe_temp_dir)


@pytest.fixture(scope="function")
def crash_analyzer(request: pytest.FixtureRequest, cprobe_temp_dir: Path) -> CrashAnalyzer:
    """Provide crash analysis capabilities."""
    return CrashAnalyzer(
        work_dir=cprobe_temp_dir,
        keep_cores=request.config.getoption("--cprobe-keep-temps")
    )


class CProbeSession:
    """Main session object for C code testing."""

    def __init__(self, compiler: CCompiler, runner: CRunner, crash_analyzer: CrashAnalyzer):
        self.compiler = compiler
        self.runner = runner
        self.crash_analyzer = crash_analyzer
        self._compiled_libs: Dict[str, ctypes.CDLL] = {}

    def compile_and_load(self, source_code: str, filename: Optional[str] = None) -> ctypes.CDLL:
        """Compile C source code and load it as a shared library."""
        if filename is None:
            filename = "test_module.c"

        # Check if sanitizers are enabled - warn about limitations
        if self.compiler.sanitizer_config:
            import warnings
            warnings.warn(
                f"Using {self.compiler.sanitizer_config.sanitizer_type.value} sanitizer with shared libraries "
                "may not work properly. Consider testing executables instead for full sanitizer support.",
                UserWarning
            )

        # Compile to shared library
        lib_path = self.compiler.compile_shared_lib(source_code, filename)

        try:
            # Load with ctypes
            lib = ctypes.CDLL(str(lib_path))
            self._compiled_libs[filename] = lib
            return lib
        except OSError as e:
            if "AddressSanitizer" in str(e) or "ASan runtime" in str(e):
                # Provide helpful error message for sanitizer issues
                raise RuntimeError(
                    f"Failed to load library with sanitizer. "
                    f"Sanitizers work better with executables. "
                    f"Try using compile_executable() instead, or run without sanitizers. "
                    f"Original error: {e}"
                ) from e
            raise

    def compile_executable(self, source_code: str, filename: Optional[str] = None) -> Path:
        """Compile C source code to an executable."""
        if filename is None:
            filename = "test_program.c"

        return self.compiler.compile_executable(source_code, filename)

    def run_executable(self, exe_path: Path, args: Optional[List[str]] = None) -> subprocess.CompletedProcess:
        """Run a compiled executable."""
        return self.runner.run(exe_path, args or [], sanitizer_config=self.compiler.sanitizer_config)

    def analyze_crash(self, exe_path: Path, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run executable and analyze crashes if they occur."""
        result = self.run_executable(exe_path, args)

        if result.returncode < 0:  # Likely crashed
            return self.crash_analyzer.analyze_crash(exe_path, args or [])

        return {"crashed": False, "returncode": result.returncode}


@pytest.fixture(scope="function")
def cprobe(c_compiler: CCompiler, c_runner: CRunner, crash_analyzer: CrashAnalyzer) -> CProbeSession:
    """Main fixture providing C code testing capabilities."""
    return CProbeSession(c_compiler, c_runner, crash_analyzer)

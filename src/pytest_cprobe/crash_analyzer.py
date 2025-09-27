"""
Crash analysis with coredump and gdb for pytest-cprobe.
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import tempfile
import re


class CrashAnalysisError(Exception):
    """Raised when crash analysis fails."""
    pass


class CrashAnalyzer:
    """Analyzer for program crashes using gdb and core dumps."""

    def __init__(
        self,
        work_dir: Optional[Path] = None,
        gdb_command: str = "gdb",
        keep_cores: bool = False
    ):
        self.work_dir = work_dir or Path(tempfile.mkdtemp())
        self.gdb_command = gdb_command
        self.keep_cores = keep_cores

        # Check if gdb is available
        if not shutil.which(self.gdb_command):
            self.gdb_available = False
        else:
            self.gdb_available = True

    def analyze_crash(
        self,
        executable: Path,
        args: Optional[List[str]] = None,
        core_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Analyze a program crash using gdb and core dump."""
        result = {
            "crashed": True,
            "gdb_available": self.gdb_available,
            "analysis": {}
        }

        # Find core file if not provided
        if core_file is None:
            core_file = self._find_core_file(executable.name)

        if core_file:
            result["core_file"] = str(core_file)

            if self.gdb_available:
                try:
                    gdb_analysis = self._analyze_with_gdb(executable, core_file)
                    result["analysis"].update(gdb_analysis)
                except CrashAnalysisError as e:
                    result["analysis"]["gdb_error"] = str(e)
        else:
            result["core_file"] = None
            result["analysis"]["error"] = "No core file found"

        return result

    def get_backtrace(self, executable: Path, core_file: Path) -> List[str]:
        """Get stack backtrace from core dump."""
        if not self.gdb_available:
            raise CrashAnalysisError("gdb not available")

        gdb_commands = [
            "set pagination off",
            "bt",
            "quit"
        ]

        try:
            result = self._run_gdb(executable, core_file, gdb_commands)

            # Parse backtrace from output
            backtrace = []
            in_backtrace = False

            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('#'):
                    in_backtrace = True
                    backtrace.append(line)
                elif in_backtrace and line and not line.startswith('(gdb)'):
                    backtrace.append(line)
                elif in_backtrace and not line:
                    break

            return backtrace

        except subprocess.SubprocessError as e:
            raise CrashAnalysisError(f"Failed to get backtrace: {e}")

    def get_registers(self, executable: Path, core_file: Path) -> Dict[str, str]:
        """Get register values from core dump."""
        if not self.gdb_available:
            raise CrashAnalysisError("gdb not available")

        gdb_commands = [
            "set pagination off",
            "info registers",
            "quit"
        ]

        try:
            result = self._run_gdb(executable, core_file, gdb_commands)

            # Parse register information
            registers = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('(gdb)') and '0x' in line:
                    # Match register lines like "rax            0x0      0"
                    match = re.match(r'(\w+)\s+(0x[0-9a-fA-F]+)', line)
                    if match:
                        reg_name, reg_value = match.groups()
                        registers[reg_name] = reg_value

            return registers

        except subprocess.SubprocessError as e:
            raise CrashAnalysisError(f"Failed to get registers: {e}")

    def get_memory_map(self, executable: Path, core_file: Path) -> List[str]:
        """Get memory mapping from core dump."""
        if not self.gdb_available:
            raise CrashAnalysisError("gdb not available")

        gdb_commands = [
            "set pagination off",
            "info proc mappings",
            "quit"
        ]

        try:
            result = self._run_gdb(executable, core_file, gdb_commands)

            # Parse memory mappings
            mappings = []
            in_mappings = False

            for line in result.stdout.split('\n'):
                line = line.strip()
                if "Start Addr" in line and "End Addr" in line:
                    in_mappings = True
                    mappings.append(line)
                elif in_mappings and line and not line.startswith('(gdb)'):
                    if line.startswith('0x'):
                        mappings.append(line)
                elif in_mappings and not line:
                    break

            return mappings

        except subprocess.SubprocessError as e:
            raise CrashAnalysisError(f"Failed to get memory map: {e}")

    def disassemble_crash_location(self, executable: Path, core_file: Path) -> List[str]:
        """Disassemble code around crash location."""
        if not self.gdb_available:
            raise CrashAnalysisError("gdb not available")

        gdb_commands = [
            "set pagination off",
            "disas /m",
            "quit"
        ]

        try:
            result = self._run_gdb(executable, core_file, gdb_commands)

            # Parse disassembly
            disassembly = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('(gdb)'):
                    disassembly.append(line)

            return disassembly

        except subprocess.SubprocessError as e:
            raise CrashAnalysisError(f"Failed to disassemble: {e}")

    def _analyze_with_gdb(self, executable: Path, core_file: Path) -> Dict[str, Any]:
        """Perform comprehensive analysis with gdb."""
        analysis = {}

        try:
            analysis["backtrace"] = self.get_backtrace(executable, core_file)
        except CrashAnalysisError:
            analysis["backtrace"] = []

        try:
            analysis["registers"] = self.get_registers(executable, core_file)
        except CrashAnalysisError:
            analysis["registers"] = {}

        try:
            analysis["memory_map"] = self.get_memory_map(executable, core_file)
        except CrashAnalysisError:
            analysis["memory_map"] = []

        try:
            analysis["disassembly"] = self.disassemble_crash_location(executable, core_file)
        except CrashAnalysisError:
            analysis["disassembly"] = []

        return analysis

    def _run_gdb(self, executable: Path, core_file: Path, commands: List[str]) -> subprocess.CompletedProcess:
        """Run gdb with given commands."""
        cmd = [
            self.gdb_command,
            "--batch",
            "--quiet",
            str(executable),
            str(core_file)
        ]

        # Add commands
        for command in commands:
            cmd.extend(["-ex", command])

        return subprocess.run(
            cmd,
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            timeout=30  # Prevent gdb from hanging
        )

    def _find_core_file(self, program_name: str) -> Optional[Path]:
        """Find core file for a program."""
        # Common core file patterns
        patterns = [
            f"core.{program_name}.*",
            "core.*",
            "core",
            f"{program_name}.core"
        ]

        for pattern in patterns:
            cores = list(self.work_dir.glob(pattern))
            if cores:
                # Return the most recent core file
                return max(cores, key=lambda p: p.stat().st_mtime)

        # Also check system core dump locations
        system_locations = [
            Path("/var/lib/systemd/coredump/"),
            Path("/tmp/"),
            Path("/var/crash/")
        ]

        for location in system_locations:
            if location.exists():
                for pattern in patterns:
                    cores = list(location.glob(pattern))
                    if cores:
                        return max(cores, key=lambda p: p.stat().st_mtime)

        return None

    def cleanup_core_files(self) -> None:
        """Clean up core files if not keeping them."""
        if not self.keep_cores:
            for core_file in self.work_dir.glob("core*"):
                try:
                    core_file.unlink()
                except OSError:
                    pass

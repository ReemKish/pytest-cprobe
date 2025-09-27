"""
Sanitizer support for pytest-cprobe.
"""

from typing import List, Dict, Any, Optional
from enum import Enum


class SanitizerType(Enum):
    """Supported sanitizer types."""
    ADDRESS = "address"
    MEMORY = "memory"
    THREAD = "thread"
    UNDEFINED = "undefined"
    LEAK = "leak"


class SanitizerConfig:
    """Configuration for C compiler sanitizers."""

    def __init__(
        self,
        sanitizer_type: str,
        additional_flags: Optional[List[str]] = None,
        detect_leaks: bool = True,
        abort_on_error: bool = True
    ):
        try:
            self.sanitizer_type = SanitizerType(sanitizer_type.lower())
        except ValueError:
            raise ValueError(f"Unsupported sanitizer type: {sanitizer_type}")

        self.additional_flags = additional_flags or []
        self.detect_leaks = detect_leaks
        self.abort_on_error = abort_on_error

    def get_compile_flags(self) -> List[str]:
        """Get compiler flags for the sanitizer."""
        flags = []

        if self.sanitizer_type == SanitizerType.ADDRESS:
            flags.extend(["-fsanitize=address", "-fno-omit-frame-pointer"])
            if self.detect_leaks:
                flags.append("-fsanitize-address-use-after-scope")

        elif self.sanitizer_type == SanitizerType.MEMORY:
            flags.extend(["-fsanitize=memory", "-fno-omit-frame-pointer"])
            flags.append("-fsanitize-memory-track-origins=2")

        elif self.sanitizer_type == SanitizerType.THREAD:
            flags.extend(["-fsanitize=thread", "-fno-omit-frame-pointer"])

        elif self.sanitizer_type == SanitizerType.UNDEFINED:
            flags.extend(["-fsanitize=undefined", "-fno-omit-frame-pointer"])

        elif self.sanitizer_type == SanitizerType.LEAK:
            flags.extend(["-fsanitize=leak", "-fno-omit-frame-pointer"])

        # Add additional flags
        flags.extend(self.additional_flags)

        return flags

    def get_runtime_env(self) -> Dict[str, str]:
        """Get environment variables for runtime sanitizer configuration."""
        env = {}

        if self.sanitizer_type == SanitizerType.ADDRESS:
            options = []
            if self.abort_on_error:
                options.append("abort_on_error=1")
            if self.detect_leaks:
                options.append("detect_leaks=1")
            else:
                options.append("detect_leaks=0")

            if options:
                env["ASAN_OPTIONS"] = ":".join(options)

        elif self.sanitizer_type == SanitizerType.MEMORY:
            options = []
            if self.abort_on_error:
                options.append("abort_on_error=1")
            options.append("print_stats=1")

            if options:
                env["MSAN_OPTIONS"] = ":".join(options)

        elif self.sanitizer_type == SanitizerType.THREAD:
            options = []
            if self.abort_on_error:
                options.append("abort_on_error=1")

            if options:
                env["TSAN_OPTIONS"] = ":".join(options)

        elif self.sanitizer_type == SanitizerType.UNDEFINED:
            options = []
            if self.abort_on_error:
                options.append("abort_on_error=1")
            options.append("print_stacktrace=1")

            if options:
                env["UBSAN_OPTIONS"] = ":".join(options)

        elif self.sanitizer_type == SanitizerType.LEAK:
            options = []
            if self.abort_on_error:
                options.append("abort_on_error=1")

            if options:
                env["LSAN_OPTIONS"] = ":".join(options)

        return env

    def parse_sanitizer_output(self, stderr: str) -> Dict[str, Any]:
        """Parse sanitizer output for structured error reporting."""
        result = {
            "sanitizer_type": self.sanitizer_type.value,
            "errors": [],
            "summary": {}
        }

        lines = stderr.split('\n')
        current_error = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # AddressSanitizer patterns
            if "AddressSanitizer" in line:
                if "ERROR" in line:
                    current_error = {"type": "address_error", "message": line, "details": []}
                    result["errors"].append(current_error)
                elif "SUMMARY" in line:
                    result["summary"]["address"] = line

            # MemorySanitizer patterns
            elif "MemorySanitizer" in line:
                if "WARNING" in line or "ERROR" in line:
                    current_error = {"type": "memory_error", "message": line, "details": []}
                    result["errors"].append(current_error)
                elif "SUMMARY" in line:
                    result["summary"]["memory"] = line

            # ThreadSanitizer patterns
            elif "ThreadSanitizer" in line:
                if "WARNING" in line or "ERROR" in line:
                    current_error = {"type": "thread_error", "message": line, "details": []}
                    result["errors"].append(current_error)
                elif "SUMMARY" in line:
                    result["summary"]["thread"] = line

            # UndefinedBehaviorSanitizer patterns
            elif "UndefinedBehaviorSanitizer" in line:
                if "ERROR" in line:
                    current_error = {"type": "undefined_error", "message": line, "details": []}
                    result["errors"].append(current_error)
                elif "SUMMARY" in line:
                    result["summary"]["undefined"] = line

            # LeakSanitizer patterns
            elif "LeakSanitizer" in line:
                if "ERROR" in line:
                    current_error = {"type": "leak_error", "message": line, "details": []}
                    result["errors"].append(current_error)
                elif "SUMMARY" in line:
                    result["summary"]["leak"] = line

            # Add details to current error
            elif current_error and line.startswith('#'):
                current_error["details"].append(line)

        return result

    def __str__(self) -> str:
        return f"SanitizerConfig({self.sanitizer_type.value})"

    def __repr__(self) -> str:
        return f"SanitizerConfig(sanitizer_type='{self.sanitizer_type.value}', additional_flags={self.additional_flags})"


def get_available_sanitizers() -> List[str]:
    """Get list of available sanitizers based on compiler support."""
    # This could be enhanced to actually check compiler support
    return [sanitizer.value for sanitizer in SanitizerType]

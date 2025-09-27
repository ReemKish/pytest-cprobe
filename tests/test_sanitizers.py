"""Tests for sanitizer functionality."""

import pytest
from pytest_cprobe.sanitizers import SanitizerConfig, SanitizerType, get_available_sanitizers


def test_sanitizer_config_creation():
    """Test creating sanitizer configurations."""
    config = SanitizerConfig("address")
    assert config.sanitizer_type == SanitizerType.ADDRESS

    config = SanitizerConfig("memory")
    assert config.sanitizer_type == SanitizerType.MEMORY


def test_invalid_sanitizer_type():
    """Test that invalid sanitizer types raise ValueError."""
    with pytest.raises(ValueError):
        SanitizerConfig("invalid_sanitizer")


def test_address_sanitizer_flags():
    """Test AddressSanitizer compile flags."""
    config = SanitizerConfig("address")
    flags = config.get_compile_flags()

    assert "-fsanitize=address" in flags
    assert "-fno-omit-frame-pointer" in flags


def test_memory_sanitizer_flags():
    """Test MemorySanitizer compile flags."""
    config = SanitizerConfig("memory")
    flags = config.get_compile_flags()

    assert "-fsanitize=memory" in flags
    assert "-fno-omit-frame-pointer" in flags
    assert "-fsanitize-memory-track-origins=2" in flags


def test_thread_sanitizer_flags():
    """Test ThreadSanitizer compile flags."""
    config = SanitizerConfig("thread")
    flags = config.get_compile_flags()

    assert "-fsanitize=thread" in flags
    assert "-fno-omit-frame-pointer" in flags


def test_undefined_sanitizer_flags():
    """Test UndefinedBehaviorSanitizer compile flags."""
    config = SanitizerConfig("undefined")
    flags = config.get_compile_flags()

    assert "-fsanitize=undefined" in flags
    assert "-fno-omit-frame-pointer" in flags


def test_leak_sanitizer_flags():
    """Test LeakSanitizer compile flags."""
    config = SanitizerConfig("leak")
    flags = config.get_compile_flags()

    assert "-fsanitize=leak" in flags
    assert "-fno-omit-frame-pointer" in flags


def test_sanitizer_runtime_env():
    """Test runtime environment variables."""
    config = SanitizerConfig("address")
    env = config.get_runtime_env()

    assert "ASAN_OPTIONS" in env
    assert "abort_on_error=1" in env["ASAN_OPTIONS"]
    assert "detect_leaks=1" in env["ASAN_OPTIONS"]


def test_sanitizer_output_parsing():
    """Test parsing sanitizer output."""
    config = SanitizerConfig("address")

    # Sample AddressSanitizer output
    stderr_output = """
==12345==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x602000000014
READ of size 4 at 0x602000000014 thread T0
    #0 0x401234 in main test.c:10
    #1 0x7f123456789a in __libc_start_main
==12345==SUMMARY: AddressSanitizer: heap-buffer-overflow test.c:10 in main
"""

    result = config.parse_sanitizer_output(stderr_output)

    assert result["sanitizer_type"] == "address"
    assert len(result["errors"]) > 0
    assert result["errors"][0]["type"] == "address_error"
    assert "heap-buffer-overflow" in result["errors"][0]["message"]


def test_get_available_sanitizers():
    """Test getting list of available sanitizers."""
    sanitizers = get_available_sanitizers()

    assert "address" in sanitizers
    assert "memory" in sanitizers
    assert "thread" in sanitizers
    assert "undefined" in sanitizers
    assert "leak" in sanitizers


@pytest.mark.skipif(
    not pytest.importorskip("shutil").which("gcc"),
    reason="gcc not available"
)
def test_compile_with_address_sanitizer(c_compiler, temp_work_dir):
    """Test compiling with AddressSanitizer (requires gcc/clang)."""
    from pytest_cprobe.sanitizers import SanitizerConfig
    from pytest_cprobe.compiler import CCompiler

    # Create compiler with AddressSanitizer
    sanitizer_config = SanitizerConfig("address")
    compiler = CCompiler(
        work_dir=temp_work_dir,
        sanitizer_config=sanitizer_config
    )

    source_code = """
    int test_function(int x) {
        return x * 2;
    }
    """

    try:
        lib_path = compiler.compile_shared_lib(source_code, "asan_test.c")
        assert lib_path.exists()
    except Exception as e:
        # Some systems may not support all sanitizers
        pytest.skip(f"Sanitizer compilation failed: {e}")

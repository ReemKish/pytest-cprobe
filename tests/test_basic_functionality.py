"""Basic functionality tests for pytest-cprobe."""

import pytest
import ctypes
from pathlib import Path


def test_cprobe_fixture_available(cprobe):
    """Test that the main cprobe fixture is available."""
    assert cprobe is not None
    assert hasattr(cprobe, 'compiler')
    assert hasattr(cprobe, 'runner')
    assert hasattr(cprobe, 'crash_analyzer')


def test_compile_and_load_simple_function(cprobe):
    """Test compiling and loading a simple C function."""
    source_code = """
    int add(int a, int b) {
        return a + b;
    }
    """
    
    lib = cprobe.compile_and_load(source_code, "simple_math.c")
    
    # Configure function signature
    lib.add.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.add.restype = ctypes.c_int
    
    # Test the function
    result = lib.add(2, 3)
    assert result == 5


def test_compile_executable(cprobe):
    """Test compiling a C program to executable."""
    source_code = """
    #include <stdio.h>
    
    int main() {
        printf("Hello, World!\\n");
        return 0;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "hello.c")
    assert exe_path.exists()
    assert exe_path.is_file()


def test_run_executable(cprobe):
    """Test running a compiled executable."""
    source_code = """
    #include <stdio.h>
    
    int main() {
        printf("Hello, pytest-cprobe!\\n");
        return 42;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "test_program.c")
    result = cprobe.run_executable(exe_path)
    
    assert result.returncode == 42
    assert "Hello, pytest-cprobe!" in result.stdout


def test_compile_with_debug_symbols(c_compiler):
    """Test compilation with debug symbols."""
    source_code = """
    int multiply(int x, int y) {
        return x * y;
    }
    """
    
    # Compiler should have debug enabled from fixture
    lib_path = c_compiler.compile_shared_lib(source_code, "debug_test.c")
    assert lib_path.exists()


def test_multiple_functions_in_library(cprobe):
    """Test loading library with multiple functions."""
    source_code = """
    int add(int a, int b) {
        return a + b;
    }
    
    int subtract(int a, int b) {
        return a - b;
    }
    
    int multiply(int a, int b) {
        return a * b;
    }
    """
    
    lib = cprobe.compile_and_load(source_code, "math_lib.c")
    
    # Configure all functions
    for func_name in ['add', 'subtract', 'multiply']:
        func = getattr(lib, func_name)
        func.argtypes = [ctypes.c_int, ctypes.c_int]
        func.restype = ctypes.c_int
    
    # Test all functions
    assert lib.add(5, 3) == 8
    assert lib.subtract(5, 3) == 2
    assert lib.multiply(5, 3) == 15


def test_executable_with_arguments(cprobe):
    """Test running executable with command line arguments."""
    source_code = """
    #include <stdio.h>
    
    int main(int argc, char *argv[]) {
        printf("argc: %d\\n", argc);
        for (int i = 0; i < argc; i++) {
            printf("argv[%d]: %s\\n", i, argv[i]);
        }
        return argc;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "args_test.c")
    result = cprobe.run_executable(exe_path, ["arg1", "arg2", "arg3"])
    
    assert result.returncode == 4  # program name + 3 args
    assert "argc: 4" in result.stdout
    assert "arg1" in result.stdout
    assert "arg2" in result.stdout
    assert "arg3" in result.stdout
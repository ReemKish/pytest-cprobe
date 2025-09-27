"""
Example demonstrating pytest-cprobe functionality.

Run with: pytest example_test.py -v
"""

import ctypes


def test_simple_math_functions(cprobe):
    """Test basic math functions compiled from C."""
    source_code = """
    int add(int a, int b) {
        return a + b;
    }

    int multiply(int a, int b) {
        return a * b;
    }

    int factorial(int n) {
        if (n <= 1) return 1;
        return n * factorial(n - 1);
    }
    """

    # Compile and load as shared library
    lib = cprobe.compile_and_load(source_code, "math_functions.c")

    # Configure function signatures
    lib.add.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.add.restype = ctypes.c_int

    lib.multiply.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.multiply.restype = ctypes.c_int

    lib.factorial.argtypes = [ctypes.c_int]
    lib.factorial.restype = ctypes.c_int

    # Test the functions
    assert lib.add(5, 3) == 8
    assert lib.multiply(4, 7) == 28
    assert lib.factorial(5) == 120


def test_hello_world_program(cprobe):
    """Test a simple C program."""
    source_code = """
    #include <stdio.h>

    int main(int argc, char *argv[]) {
        printf("Hello from C!\\n");
        printf("Arguments received: %d\\n", argc);
        return 42;
    }
    """

    # Compile to executable
    exe_path = cprobe.compile_executable(source_code, "hello.c")

    # Run the program
    result = cprobe.run_executable(exe_path, ["arg1", "arg2"])

    # Check results
    assert result.returncode == 42
    assert "Hello from C!" in result.stdout
    assert "Arguments received: 3" in result.stdout  # program name + 2 args


def test_array_operations(cprobe):
    """Test C functions that work with arrays."""
    source_code = """
    #include <string.h>

    int sum_array(int* arr, int size) {
        int sum = 0;
        for (int i = 0; i < size; i++) {
            sum += arr[i];
        }
        return sum;
    }

    void reverse_array(int* arr, int size) {
        for (int i = 0; i < size / 2; i++) {
            int temp = arr[i];
            arr[i] = arr[size - 1 - i];
            arr[size - 1 - i] = temp;
        }
    }

    void fill_array(int* arr, int size, int value) {
        for (int i = 0; i < size; i++) {
            arr[i] = value;
        }
    }
    """

    lib = cprobe.compile_and_load(source_code, "array_ops.c")

    # Configure function signatures
    lib.sum_array.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    lib.sum_array.restype = ctypes.c_int

    lib.reverse_array.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    lib.reverse_array.restype = None

    lib.fill_array.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int]
    lib.fill_array.restype = None

    # Test sum_array
    test_array = (ctypes.c_int * 5)(1, 2, 3, 4, 5)
    assert lib.sum_array(test_array, 5) == 15

    # Test reverse_array
    lib.reverse_array(test_array, 5)
    reversed_values = [test_array[i] for i in range(5)]
    assert reversed_values == [5, 4, 3, 2, 1]

    # Test fill_array
    lib.fill_array(test_array, 5, 42)
    filled_values = [test_array[i] for i in range(5)]
    assert all(v == 42 for v in filled_values)


if __name__ == "__main__":
    print("Run this with: pytest example_test.py -v")
    print("Or with sanitizers: pytest example_test.py -v --cprobe-sanitizer=address")

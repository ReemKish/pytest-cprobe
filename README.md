# pytest-cprobe

A pytest plugin for testing C code — compile, run, call functions via ctypes, enable sanitizers, and analyze crashes with coredump and gdb.

## Features

- **C Code Compilation**: Compile C source code to shared libraries or executables
- **Function Testing**: Call C functions directly from Python using ctypes  
- **Executable Testing**: Run compiled C programs and capture output
- **Sanitizer Support**: Enable AddressSanitizer, MemorySanitizer, ThreadSanitizer, UndefinedBehaviorSanitizer, and LeakSanitizer
- **Crash Analysis**: Analyze crashes using gdb and core dumps
- **Cross-platform**: Works on Linux and macOS (requires gcc or clang)

## Installation

```bash
pip install pytest-cprobe
```

## Requirements

- Python 3.8+
- pytest 6.0+
- A C compiler (gcc or clang)
- gdb (optional, for crash analysis)

## Quick Start

Here's a simple example of testing a C function:

```python
def test_math_functions(cprobe):
    source_code = """
    int add(int a, int b) {
        return a + b;
    }
    
    int multiply(int a, int b) {
        return a * b;
    }
    """
    
    # Compile and load as shared library
    lib = cprobe.compile_and_load(source_code, "math.c")
    
    # Configure function signatures
    lib.add.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.add.restype = ctypes.c_int
    
    lib.multiply.argtypes = [ctypes.c_int, ctypes.c_int] 
    lib.multiply.restype = ctypes.c_int
    
    # Test the functions
    assert lib.add(2, 3) == 5
    assert lib.multiply(4, 5) == 20
```

## Usage Examples

### Testing C Programs

```python
def test_hello_world(cprobe):
    source_code = """
    #include <stdio.h>
    
    int main() {
        printf("Hello, World!\\n");
        return 0;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "hello.c")
    result = cprobe.run_executable(exe_path)
    
    assert result.returncode == 0
    assert "Hello, World!" in result.stdout
```

### Using Sanitizers

```python
# Run tests with AddressSanitizer
pytest tests/ --cprobe-sanitizer=address

# Run tests with debug symbols
pytest tests/ --cprobe-debug

# Keep temporary files for debugging
pytest tests/ --cprobe-keep-temps
```

### Testing with Arrays and Structs

```python
import ctypes

def test_array_processing(cprobe):
    source_code = """
    int sum_array(int* arr, int size) {
        int sum = 0;
        for (int i = 0; i < size; i++) {
            sum += arr[i];
        }
        return sum;
    }
    """
    
    lib = cprobe.compile_and_load(source_code, "arrays.c")
    
    lib.sum_array.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    lib.sum_array.restype = ctypes.c_int
    
    # Test with array
    test_array = (ctypes.c_int * 5)(1, 2, 3, 4, 5)
    result = lib.sum_array(test_array, 5)
    assert result == 15

def test_structs(cprobe):
    source_code = """
    typedef struct {
        int x;
        int y;
    } Point;
    
    int point_distance_squared(Point* p1, Point* p2) {
        int dx = p1->x - p2->x;
        int dy = p1->y - p2->y;
        return dx * dx + dy * dy;
    }
    """
    
    lib = cprobe.compile_and_load(source_code, "geometry.c")
    
    # Define corresponding ctypes structure
    class Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]
    
    lib.point_distance_squared.argtypes = [ctypes.POINTER(Point), ctypes.POINTER(Point)]
    lib.point_distance_squared.restype = ctypes.c_int
    
    p1 = Point(0, 0)
    p2 = Point(3, 4)
    distance_sq = lib.point_distance_squared(ctypes.byref(p1), ctypes.byref(p2))
    assert distance_sq == 25  # 3^2 + 4^2
```

### Crash Analysis

```python
def test_crash_analysis(cprobe):
    # Code that will crash
    source_code = """
    int main() {
        int *p = 0;
        *p = 42;  // Segmentation fault
        return 0;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "crash_test.c")
    analysis = cprobe.analyze_crash(exe_path)
    
    if analysis["gdb_available"]:
        # Check crash analysis results
        assert analysis["crashed"]
        if "backtrace" in analysis["analysis"]:
            print("Crash backtrace:", analysis["analysis"]["backtrace"])
```

## Command Line Options

- `--cprobe-compiler=<compiler>`: Choose C compiler (default: gcc)
- `--cprobe-sanitizer=<type>`: Enable sanitizer (address, memory, thread, undefined, leak)
- `--cprobe-debug`: Enable debug symbols
- `--cprobe-keep-temps`: Keep temporary files for debugging

## Fixtures

### `cprobe`

The main fixture providing access to compilation and execution functionality:

- `cprobe.compile_and_load(source_code, filename)`: Compile to shared library and load with ctypes
- `cprobe.compile_executable(source_code, filename)`: Compile to executable  
- `cprobe.run_executable(exe_path, args)`: Run executable and capture output
- `cprobe.analyze_crash(exe_path, args)`: Run and analyze crashes

### `c_compiler`

Direct access to the C compiler:

- `c_compiler.compile_shared_lib(source_code, filename)`
- `c_compiler.compile_executable(source_code, filename)`
- `c_compiler.compile_object(source_code, filename)`

### `c_runner`

Direct access to the program runner:

- `c_runner.run(executable, args, stdin_data, env, timeout)`
- `c_runner.run_with_valgrind(executable, args, valgrind_args)`

### `crash_analyzer`

Direct access to crash analysis:

- `crash_analyzer.analyze_crash(executable, args, core_file)`
- `crash_analyzer.get_backtrace(executable, core_file)`
- `crash_analyzer.get_registers(executable, core_file)`

## Sanitizer Support

pytest-cprobe supports multiple sanitizers:

- **AddressSanitizer** (`address`): Detects buffer overflows, use-after-free, memory leaks
- **MemorySanitizer** (`memory`): Detects uninitialized memory reads  
- **ThreadSanitizer** (`thread`): Detects data races and thread synchronization bugs
- **UndefinedBehaviorSanitizer** (`undefined`): Detects undefined behavior
- **LeakSanitizer** (`leak`): Detects memory leaks

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License
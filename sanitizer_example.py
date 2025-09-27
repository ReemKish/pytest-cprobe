"""
Example showing sanitizer usage with executables.

Run with: pytest sanitizer_example.py -v --cprobe-sanitizer=address
"""

def test_program_without_memory_error(cprobe):
    """Test a clean program - should pass with sanitizers."""
    source_code = """
    #include <stdio.h>
    #include <stdlib.h>
    
    int main() {
        int *ptr = malloc(sizeof(int) * 10);
        if (!ptr) return 1;
        
        // Use the memory properly
        for (int i = 0; i < 10; i++) {
            ptr[i] = i * i;
        }
        
        // Print some values
        printf("ptr[5] = %d\\n", ptr[5]);
        
        // Clean up
        free(ptr);
        return 0;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "clean_program.c")
    result = cprobe.run_executable(exe_path)
    
    assert result.returncode == 0
    assert "ptr[5] = 25" in result.stdout


def test_program_with_potential_memory_issue(cprobe):
    """Test a program that might have memory issues - sanitizer should catch them."""
    source_code = """
    #include <stdio.h>
    #include <stdlib.h>
    
    int main() {
        int *ptr = malloc(sizeof(int) * 10);
        if (!ptr) return 1;
        
        // This is fine
        for (int i = 0; i < 10; i++) {
            ptr[i] = i;
        }
        
        printf("Array filled successfully\\n");
        
        // Clean up
        free(ptr);
        
        // This would be caught by AddressSanitizer if uncommented:
        // printf("After free: %d\\n", ptr[0]);  // Use after free
        
        return 0;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "safe_program.c")
    result = cprobe.run_executable(exe_path)
    
    # This should pass even with sanitizers since we're not doing anything wrong
    assert result.returncode == 0
    assert "Array filled successfully" in result.stdout


def test_simple_computation(cprobe):
    """Test mathematical computation - should work fine with sanitizers."""
    source_code = """
    #include <stdio.h>
    
    int fibonacci(int n) {
        if (n <= 1) return n;
        return fibonacci(n-1) + fibonacci(n-2);
    }
    
    int main() {
        int result = fibonacci(10);
        printf("fibonacci(10) = %d\\n", result);
        return result == 55 ? 0 : 1;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "fibonacci.c")
    result = cprobe.run_executable(exe_path)
    
    assert result.returncode == 0
    assert "fibonacci(10) = 55" in result.stdout


if __name__ == "__main__":
    print("Run this with sanitizers:")
    print("pytest sanitizer_example.py -v --cprobe-sanitizer=address")
    print("pytest sanitizer_example.py -v --cprobe-sanitizer=undefined")
    print("Or without:")
    print("pytest sanitizer_example.py -v")
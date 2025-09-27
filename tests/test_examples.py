"""Example tests showing pytest-cprobe usage patterns."""

import pytest
import ctypes


def test_string_functions(cprobe):
    """Example: Testing C string functions."""
    source_code = """
    #include <string.h>
    #include <stdlib.h>
    
    int string_length(const char* str) {
        return strlen(str);
    }
    
    int string_compare(const char* str1, const char* str2) {
        return strcmp(str1, str2);
    }
    
    void string_copy_safe(const char* src, char* dest, int max_len) {
        strncpy(dest, src, max_len - 1);
        dest[max_len - 1] = '\\0';
    }
    """
    
    lib = cprobe.compile_and_load(source_code, "string_functions.c")
    
    # Configure function signatures
    lib.string_length.argtypes = [ctypes.c_char_p]
    lib.string_length.restype = ctypes.c_int
    
    lib.string_compare.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.string_compare.restype = ctypes.c_int
    
    lib.string_copy_safe.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    lib.string_copy_safe.restype = None
    
    # Test string length
    test_string = b"Hello, World!"
    length = lib.string_length(test_string)
    assert length == len(test_string)
    
    # Test string comparison
    str1 = b"hello"
    str2 = b"hello"
    str3 = b"world"
    
    assert lib.string_compare(str1, str2) == 0  # Equal strings
    assert lib.string_compare(str1, str3) != 0  # Different strings
    
    # Test safe string copy
    source = b"Hello"
    dest_buffer = ctypes.create_string_buffer(20)
    lib.string_copy_safe(source, dest_buffer, 20)
    assert dest_buffer.value == source


def test_array_processing(cprobe):
    """Example: Testing C array processing functions."""
    source_code = """
    int sum_array(int* arr, int size) {
        int sum = 0;
        for (int i = 0; i < size; i++) {
            sum += arr[i];
        }
        return sum;
    }
    
    int find_max(int* arr, int size) {
        if (size <= 0) return 0;
        
        int max = arr[0];
        for (int i = 1; i < size; i++) {
            if (arr[i] > max) {
                max = arr[i];
            }
        }
        return max;
    }
    
    void sort_array(int* arr, int size) {
        // Simple bubble sort
        for (int i = 0; i < size - 1; i++) {
            for (int j = 0; j < size - i - 1; j++) {
                if (arr[j] > arr[j + 1]) {
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                }
            }
        }
    }
    """
    
    lib = cprobe.compile_and_load(source_code, "array_functions.c")
    
    # Configure function signatures
    lib.sum_array.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    lib.sum_array.restype = ctypes.c_int
    
    lib.find_max.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    lib.find_max.restype = ctypes.c_int
    
    lib.sort_array.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    lib.sort_array.restype = None
    
    # Test with array
    test_array = (ctypes.c_int * 5)(5, 2, 8, 1, 9)
    
    # Test sum
    total = lib.sum_array(test_array, 5)
    assert total == 25
    
    # Test max
    maximum = lib.find_max(test_array, 5)
    assert maximum == 9
    
    # Test sort
    lib.sort_array(test_array, 5)
    sorted_values = [test_array[i] for i in range(5)]
    assert sorted_values == [1, 2, 5, 8, 9]


def test_struct_handling(cprobe):
    """Example: Testing C structs with ctypes."""
    source_code = """
    typedef struct {
        int x;
        int y;
    } Point;
    
    typedef struct {
        Point top_left;
        Point bottom_right;
    } Rectangle;
    
    int point_distance_squared(Point* p1, Point* p2) {
        int dx = p1->x - p2->x;
        int dy = p1->y - p2->y;
        return dx * dx + dy * dy;
    }
    
    int rectangle_area(Rectangle* rect) {
        int width = rect->bottom_right.x - rect->top_left.x;
        int height = rect->bottom_right.y - rect->top_left.y;
        return width * height;
    }
    
    Point rectangle_center(Rectangle* rect) {
        Point center;
        center.x = (rect->top_left.x + rect->bottom_right.x) / 2;
        center.y = (rect->top_left.y + rect->bottom_right.y) / 2;
        return center;
    }
    """
    
    lib = cprobe.compile_and_load(source_code, "geometry.c")
    
    # Define corresponding ctypes structures
    class Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]
    
    class Rectangle(ctypes.Structure):
        _fields_ = [("top_left", Point), ("bottom_right", Point)]
    
    # Configure function signatures
    lib.point_distance_squared.argtypes = [ctypes.POINTER(Point), ctypes.POINTER(Point)]
    lib.point_distance_squared.restype = ctypes.c_int
    
    lib.rectangle_area.argtypes = [ctypes.POINTER(Rectangle)]
    lib.rectangle_area.restype = ctypes.c_int
    
    lib.rectangle_center.argtypes = [ctypes.POINTER(Rectangle)]
    lib.rectangle_center.restype = Point
    
    # Test point distance
    p1 = Point(0, 0)
    p2 = Point(3, 4)
    distance_sq = lib.point_distance_squared(ctypes.byref(p1), ctypes.byref(p2))
    assert distance_sq == 25  # 3^2 + 4^2 = 25
    
    # Test rectangle area
    rect = Rectangle(Point(0, 0), Point(10, 5))
    area = lib.rectangle_area(ctypes.byref(rect))
    assert area == 50
    
    # Test rectangle center
    center = lib.rectangle_center(ctypes.byref(rect))
    assert center.x == 5
    assert center.y == 2  # Note: integer division


def test_program_with_file_io(cprobe, temp_work_dir):
    """Example: Testing a program that reads/writes files."""
    source_code = """
    #include <stdio.h>
    #include <stdlib.h>
    
    int main(int argc, char* argv[]) {
        if (argc != 3) {
            fprintf(stderr, "Usage: %s input_file output_file\\n", argv[0]);
            return 1;
        }
        
        FILE* input = fopen(argv[1], "r");
        if (!input) {
            perror("Failed to open input file");
            return 2;
        }
        
        FILE* output = fopen(argv[2], "w");
        if (!output) {
            perror("Failed to open output file");
            fclose(input);
            return 3;
        }
        
        int ch;
        while ((ch = fgetc(input)) != EOF) {
            fputc(ch, output);
        }
        
        fclose(input);
        fclose(output);
        
        printf("File copied successfully\\n");
        return 0;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "file_copy.c")
    
    # Create test input file
    input_file = temp_work_dir / "input.txt"
    input_file.write_text("Hello, file I/O test!\n")
    
    output_file = temp_work_dir / "output.txt"
    
    # Run the program
    result = cprobe.run_executable(exe_path, [str(input_file), str(output_file)])
    
    assert result.returncode == 0
    assert "File copied successfully" in result.stdout
    assert output_file.exists()
    assert output_file.read_text() == input_file.read_text()
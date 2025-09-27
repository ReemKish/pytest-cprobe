import ctypes

def test_simple_add(cprobe):
    source_code = """
    int add(int a, int b) {
        return a + b;
    }
    """
    
    lib = cprobe.compile_and_load(source_code, "simple.c")
    lib.add.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.add.restype = ctypes.c_int
    
    assert lib.add(2, 3) == 5

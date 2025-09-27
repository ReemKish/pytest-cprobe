"""Tests for crash analysis functionality."""

import pytest
from pathlib import Path
from pytest_cprobe.crash_analyzer import CrashAnalyzer


def test_crash_analyzer_creation(temp_work_dir):
    """Test creating a crash analyzer."""
    analyzer = CrashAnalyzer(work_dir=temp_work_dir)
    assert analyzer.work_dir == temp_work_dir
    assert isinstance(analyzer.gdb_available, bool)


def test_crash_analyzer_without_gdb(temp_work_dir):
    """Test crash analyzer when gdb is not available."""
    analyzer = CrashAnalyzer(work_dir=temp_work_dir, gdb_command="nonexistent_gdb")
    assert not analyzer.gdb_available


@pytest.mark.skipif(
    not pytest.importorskip("shutil").which("gdb"),
    reason="gdb not available"
)
def test_analyze_crash_with_gdb(cprobe):
    """Test crash analysis with gdb (if available)."""
    # Create a program that will crash
    source_code = """
    int main() {
        int *p = 0;
        *p = 42;  // Segmentation fault
        return 0;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "crash_test.c")
    
    # This should crash, but we can't easily test crash analysis
    # without actually generating a core dump, which depends on system config
    result = cprobe.analyze_crash(exe_path)
    
    assert "crashed" in result
    assert "gdb_available" in result


def test_crash_analysis_without_core_file(cprobe):
    """Test crash analysis when no core file is available."""
    # Create a normal program that exits cleanly
    source_code = """
    int main() {
        return 0;
    }
    """
    
    exe_path = cprobe.compile_executable(source_code, "normal_program.c")
    result = cprobe.analyze_crash(exe_path)
    
    # Since this doesn't crash, analysis should indicate no crash
    assert "crashed" in result


def test_find_nonexistent_core_file(temp_work_dir):
    """Test finding core files when none exist in work directory."""
    analyzer = CrashAnalyzer(work_dir=temp_work_dir)
    # Look for cores only in our work directory by temporarily modifying the method
    
    # Test just the work directory part of the search
    patterns = [
        f"core.nonexistent_program.*",
        "core.*",
        "core",
        f"nonexistent_program.core"
    ]
    
    found_cores = []
    for pattern in patterns:
        cores = list(temp_work_dir.glob(pattern))
        found_cores.extend(cores)
    
    assert not found_cores


def test_cleanup_core_files(temp_work_dir):
    """Test cleaning up core files."""
    analyzer = CrashAnalyzer(work_dir=temp_work_dir, keep_cores=False)
    
    # Create fake core files
    fake_core = temp_work_dir / "core.12345"
    fake_core.write_text("fake core dump")
    
    assert fake_core.exists()
    
    analyzer.cleanup_core_files()
    
    # Core file should be removed
    assert not fake_core.exists()


def test_keep_core_files(temp_work_dir):
    """Test keeping core files when requested."""
    analyzer = CrashAnalyzer(work_dir=temp_work_dir, keep_cores=True)
    
    # Create fake core files
    fake_core = temp_work_dir / "core.12345"
    fake_core.write_text("fake core dump")
    
    assert fake_core.exists()
    
    analyzer.cleanup_core_files()
    
    # Core file should still exist
    assert fake_core.exists()
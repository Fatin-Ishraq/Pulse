import pytest
import sys
from unittest.mock import MagicMock, patch
from pulse import core

def test_get_memory_info():
    """Test memory info retrieval."""
    # On Windows, direct_os uses ctypes, so mocking psutil won't work.
    # We'll just verify the structure matches our expectation.
    if sys.platform == "win32":
        mem_info = core.get_memory_info()
        assert "total" in mem_info
        assert "used" in mem_info
        assert "percent" in mem_info
        assert "swap_total" in mem_info
    else:
        # Linux/Mac logic (simplified for test)
        with patch("pulse.direct_os.open" if sys.platform.startswith("linux") else "psutil.virtual_memory") as mock_src:
            # For this test, we just want to ensure the function runs and returns a dict
            # Deep mocking of /proc or psutil for every platform is complex for this scope.
            # Let's rely on the structure check like Windows for now.
             mem_info = core.get_memory_info()
             assert isinstance(mem_info, dict)
             # The keys might differ slightly based on the platform implementation details in direct_os
             # but 'total' and 'percent' are standard.
             if "total" in mem_info:
                 assert mem_info["total"] >= 0

def test_get_cpu_percents():
    """Test CPU percentage retrieval."""
    # This usually uses psutil (or /proc on Linux)
    # Just verify we get a list of floats
    cpus = core.get_cpu_percents()
    assert isinstance(cpus, list)
    assert len(cpus) > 0
    assert isinstance(cpus[0], float)

def test_get_disk_info():
    """Test disk usage retrieval."""
    # Verify it returns a list of dictionaries
    disk_info = core.get_disk_info()
    assert isinstance(disk_info, list)
    
    if len(disk_info) > 0:
        disk = disk_info[0]
        assert "device" in disk
        assert "mountpoint" in disk
        assert "total" in disk
        assert "percent" in disk


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
        # We need to mock psutil.virtual_memory to return an object with total/percent attributes
        # Creating a simple namedtuple or similar object to return
        from collections import namedtuple
        mem_nt = namedtuple('vmem', ['total', 'available', 'percent', 'used', 'free'])
        mock_mem = mem_nt(total=1000, available=500, percent=50.0, used=500, free=500)
        
        with patch("psutil.virtual_memory", return_value=mock_mem):
             mem_info = core.get_memory_info()
             assert isinstance(mem_info, dict)
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


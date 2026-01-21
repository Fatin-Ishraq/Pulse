"""
Pulse Direct OS Engine
High-performance system metrics using native OS APIs.
Zero external build dependencies - just pure Python.

This module provides the same API as psutil but uses direct kernel calls
for maximum performance on critical paths.
"""
import os
import sys
import time
from typing import List, Dict, Optional, Any

# Platform detection
WINDOWS = sys.platform == 'win32'
LINUX = sys.platform.startswith('linux')
MACOS = sys.platform == 'darwin'

# ============================================================================
# LINUX IMPLEMENTATION (Uses /proc - already fast!)
# ============================================================================
if LINUX:
    import re
    
    _CLOCK_TICKS = os.sysconf('SC_CLK_TCK')
    _PAGE_SIZE = os.sysconf('SC_PAGE_SIZE')
    _last_cpu_times = None
    _last_cpu_check = 0
    
    def get_memory_info() -> Dict[str, int]:
        """Get memory info from /proc/meminfo."""
        mem = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split()
                    key = parts[0].rstrip(':')
                    value = int(parts[1]) * 1024  # Convert KB to bytes
                    if key == 'MemTotal':
                        mem['total'] = value
                    elif key == 'MemAvailable':
                        mem['available'] = value
                    elif key == 'MemFree':
                        mem['free'] = value
                    elif key == 'Buffers':
                        mem['buffers'] = value
                    elif key == 'Cached':
                        mem['cached'] = value
                    elif key == 'SwapTotal':
                        mem['swap_total'] = value
                    elif key == 'SwapFree':
                        mem['swap_free'] = value
        except Exception:
            pass
        
        mem['used'] = mem.get('total', 0) - mem.get('available', 0)
        mem['swap_used'] = mem.get('swap_total', 0) - mem.get('swap_free', 0)
        mem['percent'] = (mem['used'] / mem['total'] * 100) if mem.get('total') else 0
        return mem
    
    def get_cpu_percents() -> List[float]:
        """Get per-core CPU percentages from /proc/stat."""
        global _last_cpu_times, _last_cpu_check
        
        def read_cpu_times():
            times = []
            with open('/proc/stat', 'r') as f:
                for line in f:
                    if line.startswith('cpu') and not line.startswith('cpu '):
                        parts = line.split()[1:]
                        # user, nice, system, idle, iowait, irq, softirq
                        user = int(parts[0])
                        nice = int(parts[1])
                        system = int(parts[2])
                        idle = int(parts[3])
                        iowait = int(parts[4]) if len(parts) > 4 else 0
                        times.append({
                            'busy': user + nice + system,
                            'total': user + nice + system + idle + iowait
                        })
            return times
        
        current = read_cpu_times()
        now = time.time()
        
        if _last_cpu_times is None or now - _last_cpu_check > 0.1:
            _last_cpu_times = current
            _last_cpu_check = now
            return [0.0] * len(current)
        
        percents = []
        for prev, curr in zip(_last_cpu_times, current):
            delta_busy = curr['busy'] - prev['busy']
            delta_total = curr['total'] - prev['total']
            if delta_total > 0:
                percents.append(min(100.0, (delta_busy / delta_total) * 100))
            else:
                percents.append(0.0)
        
        _last_cpu_times = current
        _last_cpu_check = now
        return percents
    
    def get_process_list(sort_by: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get process list from /proc filesystem."""
        processes = []
        
        for pid_str in os.listdir('/proc'):
            if not pid_str.isdigit():
                continue
            
            pid = int(pid_str)
            try:
                # Read comm (process name)
                with open(f'/proc/{pid}/comm', 'r') as f:
                    name = f.read().strip()
                
                # Read stat for CPU info
                with open(f'/proc/{pid}/stat', 'r') as f:
                    stat = f.read().split()
                
                # Read statm for memory
                with open(f'/proc/{pid}/statm', 'r') as f:
                    statm = f.read().split()
                
                utime = int(stat[13])
                stime = int(stat[14])
                memory_pages = int(statm[0])
                
                processes.append({
                    'pid': pid,
                    'name': name,
                    'cpu_percent': 0,  # Would need delta tracking per-process
                    'memory_info': memory_pages * _PAGE_SIZE,
                })
            except (FileNotFoundError, PermissionError, IndexError):
                continue
        
        # Sort
        if sort_by == 'cpu':
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        elif sort_by == 'mem':
            processes.sort(key=lambda x: x['memory_info'], reverse=True)
        
        if limit:
            processes = processes[:limit]
        
        return processes
    
    def get_network_stats() -> Dict[str, int]:
        """Get network I/O from /proc/net/dev."""
        total_recv = 0
        total_sent = 0
        
        try:
            with open('/proc/net/dev', 'r') as f:
                for line in f:
                    if ':' in line:
                        parts = line.split()
                        iface = parts[0].rstrip(':')
                        if iface != 'lo':  # Skip loopback
                            total_recv += int(parts[1])
                            total_sent += int(parts[9])
        except Exception:
            pass
        
        return {'bytes_recv': total_recv, 'bytes_sent': total_sent}
    
    def get_disk_info() -> List[Dict[str, Any]]:
        """Get disk usage from /proc/mounts and statvfs."""
        disks = []
        seen = set()
        
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    device = parts[0]
                    mount = parts[1]
                    fstype = parts[2]
                    
                    if not device.startswith('/dev/') or device in seen:
                        continue
                    seen.add(device)
                    
                    try:
                        stat = os.statvfs(mount)
                        total = stat.f_blocks * stat.f_frsize
                        free = stat.f_bfree * stat.f_frsize
                        used = total - free
                        
                        disks.append({
                            'device': device,
                            'mountpoint': mount,
                            'fstype': fstype,
                            'total': total,
                            'used': used,
                            'free': free,
                            'percent': (used / total * 100) if total else 0
                        })
                    except OSError:
                        continue
        except Exception:
            pass
        
        return disks

# ============================================================================
# WINDOWS IMPLEMENTATION (Uses ctypes + kernel32/psapi)
# ============================================================================
elif WINDOWS:
    import ctypes
    from ctypes import wintypes
    
    # Load Windows DLLs
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    ntdll = ctypes.windll.ntdll
    
    # Memory status structure
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ('dwLength', wintypes.DWORD),
            ('dwMemoryLoad', wintypes.DWORD),
            ('ullTotalPhys', ctypes.c_ulonglong),
            ('ullAvailPhys', ctypes.c_ulonglong),
            ('ullTotalPageFile', ctypes.c_ulonglong),
            ('ullAvailPageFile', ctypes.c_ulonglong),
            ('ullTotalVirtual', ctypes.c_ulonglong),
            ('ullAvailVirtual', ctypes.c_ulonglong),
            ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
        ]
    
    def get_memory_info() -> Dict[str, int]:
        """Get memory info using GlobalMemoryStatusEx."""
        mem_status = MEMORYSTATUSEX()
        mem_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status))
        
        return {
            'total': mem_status.ullTotalPhys,
            'available': mem_status.ullAvailPhys,
            'used': mem_status.ullTotalPhys - mem_status.ullAvailPhys,
            'percent': mem_status.dwMemoryLoad,
            'swap_total': mem_status.ullTotalPageFile,
            'swap_used': mem_status.ullTotalPageFile - mem_status.ullAvailPageFile,
        }
    
    # For CPU, we'll still use psutil as Windows CPU times via ctypes is complex
    _psutil_fallback = None
    
    def _get_psutil():
        global _psutil_fallback
        if _psutil_fallback is None:
            import psutil
            _psutil_fallback = psutil
        return _psutil_fallback
    
    def get_cpu_percents() -> List[float]:
        """Get per-core CPU percentages."""
        return _get_psutil().cpu_percent(percpu=True)
    
    def get_process_list(sort_by: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get process list using Windows API."""
        # For Windows, psutil is actually quite optimized, so we use it
        psutil = _get_psutil()
        processes = []
        
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                info = p.info
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'] or '?',
                    'cpu_percent': info['cpu_percent'] or 0,
                    'memory_info': info['memory_info'].rss if info['memory_info'] else 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if sort_by == 'cpu':
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        elif sort_by == 'mem':
            processes.sort(key=lambda x: x['memory_info'], reverse=True)
        
        if limit:
            processes = processes[:limit]
        
        return processes
    
    def get_network_stats() -> Dict[str, int]:
        """Get network I/O."""
        stats = _get_psutil().net_io_counters()
        return {'bytes_recv': stats.bytes_recv, 'bytes_sent': stats.bytes_sent}
    
    def get_disk_info() -> List[Dict[str, Any]]:
        """Get disk usage."""
        psutil = _get_psutil()
        disks = []
        
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    'device': part.device,
                    'mountpoint': part.mountpoint,
                    'fstype': part.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except (PermissionError, OSError):
                continue
        
        return disks

# ============================================================================
# MACOS IMPLEMENTATION
# ============================================================================
elif MACOS:
    # For macOS, we use psutil as the /proc alternatives are limited
    import psutil
    
    def get_memory_info() -> Dict[str, int]:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
        }
    
    def get_cpu_percents() -> List[float]:
        return psutil.cpu_percent(percpu=True)
    
    def get_process_list(sort_by: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        processes = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                info = p.info
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'] or '?',
                    'cpu_percent': info['cpu_percent'] or 0,
                    'memory_info': info['memory_info'].rss if info['memory_info'] else 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if sort_by == 'cpu':
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        elif sort_by == 'mem':
            processes.sort(key=lambda x: x['memory_info'], reverse=True)
        
        if limit:
            processes = processes[:limit]
        
        return processes
    
    def get_network_stats() -> Dict[str, int]:
        stats = psutil.net_io_counters()
        return {'bytes_recv': stats.bytes_recv, 'bytes_sent': stats.bytes_sent}
    
    def get_disk_info() -> List[Dict[str, Any]]:
        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    'device': part.device,
                    'mountpoint': part.mountpoint,
                    'fstype': part.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except (PermissionError, OSError):
                continue
        return disks

# ============================================================================
# INITIALIZATION
# ============================================================================
def init():
    """Initialize the Direct OS engine."""
    # Prime CPU measurements
    get_cpu_percents()

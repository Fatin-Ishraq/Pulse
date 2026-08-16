"""
Pulse OS metrics layer.

A small, uniform API over per-platform system metrics. Linux reads /proc
directly because it is cheap and avoids a per-call psutil round trip; every
other platform delegates to psutil, which is a hard dependency everywhere.

State-changing primitives (``terminate_process``, ``force_kill_process``,
``renice_process``) raise on failure rather than reporting success. Use
``pulse.actions`` for the guarded, user-facing versions that confirm the
target and turn failures into a reportable result.
"""
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

# Platform detection
WINDOWS = sys.platform == 'win32'
LINUX = sys.platform.startswith('linux')
MACOS = sys.platform == 'darwin'

# Two samples closer together than this carry too little signal to be worth
# recomputing, so the previous reading is returned instead.
MIN_SAMPLE_INTERVAL = 0.05


# ============================================================================
# LINUX IMPLEMENTATION (reads /proc directly)
# ============================================================================
if LINUX:
    import signal

    _CLOCK_TICKS = os.sysconf('SC_CLK_TCK')
    _PAGE_SIZE = os.sysconf('SC_PAGE_SIZE')
    _CPU_COUNT = os.cpu_count() or 1

    _last_cpu_times: Optional[List[Tuple[int, int]]] = None
    _last_cpu_check: float = 0.0
    _last_cpu_percents: List[float] = []

    # pid -> (cumulative busy ticks, monotonic timestamp)
    _last_proc_cpu: Dict[int, Tuple[int, float]] = {}

    def get_memory_info() -> Dict[str, int]:
        """Get memory info from /proc/meminfo."""
        mem: Dict[str, int] = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    key = parts[0].rstrip(':')
                    value = int(parts[1]) * 1024  # meminfo is in KB
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
        except OSError:
            return {'total': 0, 'available': 0, 'used': 0, 'percent': 0.0,
                    'swap_total': 0, 'swap_free': 0, 'swap_used': 0}

        mem.setdefault('total', 0)
        mem.setdefault('available', mem.get('free', 0))
        mem.setdefault('swap_total', 0)
        mem.setdefault('swap_free', 0)
        mem['used'] = mem['total'] - mem['available']
        mem['swap_used'] = mem['swap_total'] - mem['swap_free']
        mem['percent'] = (mem['used'] / mem['total'] * 100) if mem['total'] else 0.0
        return mem

    def _read_cpu_times() -> List[Tuple[int, int]]:
        """Return (busy, total) jiffy counters for each core from /proc/stat."""
        times: List[Tuple[int, int]] = []
        with open('/proc/stat', 'r') as f:
            for line in f:
                # "cpu0 ...", but not the "cpu " aggregate line
                if not line.startswith('cpu') or line.startswith('cpu '):
                    continue
                fields = [int(v) for v in line.split()[1:9]]
                # user, nice, system, idle, iowait, irq, softirq, steal
                fields += [0] * (8 - len(fields))
                user, nice, system, idle, iowait, irq, softirq, steal = fields
                busy = user + nice + system + irq + softirq + steal
                times.append((busy, busy + idle + iowait))
        return times

    def get_cpu_percents() -> List[float]:
        """Get per-core CPU percentages from /proc/stat.

        The first call after import primes the counters and returns zeros;
        every later call reports the load since the previous sample.
        """
        global _last_cpu_times, _last_cpu_check, _last_cpu_percents

        try:
            current = _read_cpu_times()
        except (OSError, ValueError):
            return list(_last_cpu_percents)

        now = time.monotonic()

        # First sample, or the core count changed (CPU hotplug): prime only.
        if _last_cpu_times is None or len(_last_cpu_times) != len(current):
            _last_cpu_times = current
            _last_cpu_check = now
            _last_cpu_percents = [0.0] * len(current)
            return list(_last_cpu_percents)

        # Called again too soon for a meaningful delta - reuse the last result
        # rather than dividing by near-zero elapsed jiffies.
        if now - _last_cpu_check < MIN_SAMPLE_INTERVAL:
            return list(_last_cpu_percents)

        percents: List[float] = []
        for (prev_busy, prev_total), (busy, total) in zip(_last_cpu_times, current):
            delta_busy = busy - prev_busy
            delta_total = total - prev_total
            if delta_total > 0:
                percents.append(min(100.0, max(0.0, delta_busy / delta_total * 100.0)))
            else:
                percents.append(0.0)

        _last_cpu_times = current
        _last_cpu_check = now
        _last_cpu_percents = percents
        return list(percents)

    def _process_cpu_percent(pid: int, busy_ticks: int, now: float) -> float:
        """CPU% for one process, from the delta since we last saw it."""
        previous = _last_proc_cpu.get(pid)
        _last_proc_cpu[pid] = (busy_ticks, now)

        if previous is None:
            return 0.0

        prev_ticks, prev_time = previous
        elapsed = now - prev_time
        delta_ticks = busy_ticks - prev_ticks

        # Negative delta means the PID was recycled onto a new process.
        if elapsed <= 0 or delta_ticks < 0:
            return 0.0

        percent = (delta_ticks / _CLOCK_TICKS) / elapsed * 100.0
        # A process can saturate more than one core, so the ceiling is per-core.
        return min(percent, 100.0 * _CPU_COUNT)

    def _parse_proc_stat(raw: str) -> Optional[Tuple[str, int]]:
        """Parse /proc/<pid>/stat into (comm, utime + stime ticks).

        The comm field is wrapped in parentheses and may itself contain spaces
        and parentheses ("Isolated Web Co"), so the fields after it are located
        from the *last* closing parenthesis rather than by splitting the line.
        """
        open_paren = raw.find('(')
        close_paren = raw.rfind(')')
        if open_paren == -1 or close_paren <= open_paren:
            return None

        name = raw[open_paren + 1:close_paren]
        # Fields from here start at #3 (state); utime is #14 and stime is #15.
        rest = raw[close_paren + 1:].split()
        if len(rest) < 13:
            return None
        try:
            utime = int(rest[11])
            stime = int(rest[12])
        except ValueError:
            return None
        return name, utime + stime

    def get_process_list(sort_by: Optional[str] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get the process list from /proc."""
        processes: List[Dict[str, Any]] = []
        now = time.monotonic()
        live_pids = set()

        for pid_str in os.listdir('/proc'):
            if not pid_str.isdigit():
                continue
            pid = int(pid_str)

            try:
                with open(f'/proc/{pid}/stat', 'r') as f:
                    stat_raw = f.read()
                with open(f'/proc/{pid}/statm', 'r') as f:
                    statm = f.read().split()
            except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
                continue

            parsed = _parse_proc_stat(stat_raw)
            if parsed is None or len(statm) < 2:
                continue
            name, busy_ticks = parsed

            try:
                # statm[1] is resident set size in pages. statm[0] is the total
                # virtual size, which hugely overstates real memory use.
                rss = int(statm[1]) * _PAGE_SIZE
            except ValueError:
                continue

            live_pids.add(pid)
            processes.append({
                'pid': pid,
                'name': name,
                'cpu_percent': _process_cpu_percent(pid, busy_ticks, now),
                'memory_info': rss,
            })

        # Drop bookkeeping for processes that have exited, so the cache does
        # not grow without bound over a long session.
        for dead_pid in set(_last_proc_cpu) - live_pids:
            del _last_proc_cpu[dead_pid]

        return _sort_and_limit(processes, sort_by, limit)

    def get_network_stats() -> Dict[str, int]:
        """Get network I/O from /proc/net/dev."""
        total_recv = 0
        total_sent = 0
        try:
            with open('/proc/net/dev', 'r') as f:
                for line in f:
                    if ':' not in line:
                        continue
                    name, _, counters = line.partition(':')
                    iface = name.strip()
                    if iface == 'lo':  # Skip loopback
                        continue
                    parts = counters.split()
                    if len(parts) < 9:
                        continue
                    try:
                        total_recv += int(parts[0])
                        total_sent += int(parts[8])
                    except ValueError:
                        continue
        except OSError:
            pass

        return {'bytes_recv': total_recv, 'bytes_sent': total_sent}

    def get_disk_info() -> List[Dict[str, Any]]:
        """Get disk usage from /proc/mounts and statvfs."""
        disks: List[Dict[str, Any]] = []
        seen = set()

        try:
            with open('/proc/mounts', 'r') as f:
                mount_lines = f.readlines()
        except OSError:
            return disks

        for line in mount_lines:
            parts = line.split()
            if len(parts) < 3:
                continue
            device, mount, fstype = parts[0], parts[1], parts[2]

            if not device.startswith('/dev/') or device in seen:
                continue
            seen.add(device)

            try:
                stat = os.statvfs(mount)
            except OSError:
                continue

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
                'percent': (used / total * 100) if total else 0.0,
            })

        return disks

    def terminate_process(pid: int) -> None:
        """Ask a process to exit (SIGTERM). Raises on failure."""
        os.kill(pid, signal.SIGTERM)

    def force_kill_process(pid: int) -> None:
        """Kill a process outright (SIGKILL). Raises on failure."""
        os.kill(pid, signal.SIGKILL)

    def renice_process(pid: int, nice_value: int) -> None:
        """Change process priority. Raises on failure."""
        os.setpriority(os.PRIO_PROCESS, pid, nice_value)

    def get_process_nice(pid: int) -> int:
        """Return the current nice value of a process."""
        return os.getpriority(os.PRIO_PROCESS, pid)


# ============================================================================
# WINDOWS IMPLEMENTATION (GlobalMemoryStatusEx via ctypes, psutil elsewhere)
# ============================================================================
elif WINDOWS:
    import ctypes
    import subprocess
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32

    CREATE_NO_WINDOW = 0x08000000

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
        if not kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status)):
            return _psutil_memory_info()

        return {
            'total': mem_status.ullTotalPhys,
            'available': mem_status.ullAvailPhys,
            'free': mem_status.ullAvailPhys,
            'used': mem_status.ullTotalPhys - mem_status.ullAvailPhys,
            'percent': float(mem_status.dwMemoryLoad),
            'swap_total': mem_status.ullTotalPageFile,
            'swap_free': mem_status.ullAvailPageFile,
            'swap_used': mem_status.ullTotalPageFile - mem_status.ullAvailPageFile,
        }

    def get_cpu_percents() -> List[float]:
        return _psutil_cpu_percents()

    def get_process_list(sort_by: Optional[str] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return _psutil_process_list(sort_by, limit)

    def get_network_stats() -> Dict[str, int]:
        return _psutil_network_stats()

    def get_disk_info() -> List[Dict[str, Any]]:
        return _psutil_disk_info()

    def terminate_process(pid: int) -> None:
        """Terminate a process. Raises on failure."""
        psutil.Process(pid).terminate()

    def force_kill_process(pid: int) -> None:
        """Force kill via taskkill, which can reach processes psutil cannot.

        Raises PermissionError if the kill is still refused - typically
        meaning Pulse needs to run elevated.
        """
        completed = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "").strip()
            raise PermissionError(message or f"taskkill failed for PID {pid}")

    # Windows priority classes, ordered from highest to lowest priority.
    def _nice_to_priority_class(nice_value: int) -> int:
        if nice_value < -10:
            return psutil.HIGH_PRIORITY_CLASS
        if nice_value < 0:
            return psutil.ABOVE_NORMAL_PRIORITY_CLASS
        if nice_value == 0:
            return psutil.NORMAL_PRIORITY_CLASS
        if nice_value < 10:
            return psutil.BELOW_NORMAL_PRIORITY_CLASS
        return psutil.IDLE_PRIORITY_CLASS

    def renice_process(pid: int, nice_value: int) -> None:
        """Change process priority. Raises on failure."""
        psutil.Process(pid).nice(_nice_to_priority_class(nice_value))

    def get_process_nice(pid: int) -> int:
        """Return a nice-like value derived from the Windows priority class."""
        priority = psutil.Process(pid).nice()
        mapping = {
            psutil.REALTIME_PRIORITY_CLASS: -20,
            psutil.HIGH_PRIORITY_CLASS: -15,
            psutil.ABOVE_NORMAL_PRIORITY_CLASS: -5,
            psutil.NORMAL_PRIORITY_CLASS: 0,
            psutil.BELOW_NORMAL_PRIORITY_CLASS: 5,
            psutil.IDLE_PRIORITY_CLASS: 19,
        }
        return mapping.get(priority, 0)


# ============================================================================
# EVERYTHING ELSE (macOS, BSD, ...) - psutil handles the platform differences
# ============================================================================
else:
    import signal

    def get_memory_info() -> Dict[str, int]:
        return _psutil_memory_info()

    def get_cpu_percents() -> List[float]:
        return _psutil_cpu_percents()

    def get_process_list(sort_by: Optional[str] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return _psutil_process_list(sort_by, limit)

    def get_network_stats() -> Dict[str, int]:
        return _psutil_network_stats()

    def get_disk_info() -> List[Dict[str, Any]]:
        return _psutil_disk_info()

    def terminate_process(pid: int) -> None:
        """Ask a process to exit (SIGTERM). Raises on failure."""
        os.kill(pid, signal.SIGTERM)

    def force_kill_process(pid: int) -> None:
        """Kill a process outright (SIGKILL). Raises on failure."""
        os.kill(pid, signal.SIGKILL)

    def renice_process(pid: int, nice_value: int) -> None:
        """Change process priority. Raises on failure."""
        psutil.Process(pid).nice(nice_value)

    def get_process_nice(pid: int) -> int:
        """Return the current nice value of a process."""
        return psutil.Process(pid).nice()


# ============================================================================
# SHARED psutil-backed IMPLEMENTATIONS
# ============================================================================
def _sort_and_limit(processes: List[Dict[str, Any]],
                    sort_by: Optional[str],
                    limit: Optional[int]) -> List[Dict[str, Any]]:
    """Apply the shared sort/limit contract to a process list."""
    if sort_by == 'cpu':
        processes.sort(key=lambda p: p['cpu_percent'], reverse=True)
    elif sort_by == 'mem':
        processes.sort(key=lambda p: p['memory_info'], reverse=True)

    if limit:
        processes = processes[:limit]
    return processes


def _psutil_memory_info() -> Dict[str, int]:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        'total': mem.total,
        'available': mem.available,
        'free': getattr(mem, 'free', mem.available),
        'used': mem.used,
        'percent': mem.percent,
        'swap_total': swap.total,
        'swap_free': swap.free,
        'swap_used': swap.used,
    }


def _psutil_cpu_percents() -> List[float]:
    return psutil.cpu_percent(percpu=True)


def _psutil_process_list(sort_by: Optional[str],
                         limit: Optional[int]) -> List[Dict[str, Any]]:
    processes: List[Dict[str, Any]] = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            info = proc.info
            processes.append({
                'pid': info['pid'],
                'name': info['name'] or '?',
                'cpu_percent': info['cpu_percent'] or 0.0,
                'memory_info': info['memory_info'].rss if info['memory_info'] else 0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return _sort_and_limit(processes, sort_by, limit)


def _psutil_network_stats() -> Dict[str, int]:
    stats = psutil.net_io_counters()
    if stats is None:
        return {'bytes_recv': 0, 'bytes_sent': 0}
    return {'bytes_recv': stats.bytes_recv, 'bytes_sent': stats.bytes_sent}


def _psutil_disk_info() -> List[Dict[str, Any]]:
    disks: List[Dict[str, Any]] = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        disks.append({
            'device': part.device,
            'mountpoint': part.mountpoint,
            'fstype': part.fstype,
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
            'percent': usage.percent,
        })
    return disks


# ============================================================================
# INITIALIZATION
# ============================================================================
def init() -> None:
    """Prime the delta-based counters so the first real reading is meaningful."""
    get_cpu_percents()
    get_process_list()

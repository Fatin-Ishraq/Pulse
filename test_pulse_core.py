import pulse_core
import time

print("Initializing Pulse Core...")
pulse_core.init_system()

print("CPU Percents:", pulse_core.get_cpu_percents())
print("Memory Info:", pulse_core.get_memory_info())
print("Network Stats:", pulse_core.get_network_stats())
print("Process List (top 3 by CPU):")
procs = pulse_core.get_process_list("cpu", 3)
for p in procs:
    print(f"  PID: {p['pid']}, Name: {p['name']}, CPU: {p['cpu_percent']:.1f}%")

print("Disk Info:")
disks = pulse_core.get_disk_info()
for d in disks:
    print(f"  Mount: {d['mount_point']}, Total: {d['total_space'] / (1024**3):.1f} GB")

"""
Pulse Core - Hardware Interface Layer
Unified access to system metrics using Direct OS Engine.
"""
from pulse import direct_os

# Re-export all functions from direct_os
init = direct_os.init
get_memory_info = direct_os.get_memory_info
get_cpu_percents = direct_os.get_cpu_percents
get_process_list = direct_os.get_process_list
get_network_stats = direct_os.get_network_stats
get_disk_info = direct_os.get_disk_info

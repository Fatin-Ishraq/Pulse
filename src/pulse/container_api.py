"""
Pulse Container API
Interface for interacting with the Docker engine.
"""
import logging
from typing import List, Dict, Any, Optional

try:
    import docker
    from docker.errors import DockerException, APIError
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False

class ContainerController:
    """Controller for Docker container operations."""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self.connect()

    def connect(self) -> bool:
        """Attempt to connect to the Docker daemon."""
        if not HAS_DOCKER:
            return False
            
        try:
            self.client = docker.from_env()
            self.client.ping()
            self.connected = True
            return True
        except (DockerException, APIError):
            self.client = None
            self.connected = False
            return False

    def is_available(self) -> bool:
        """Check if Docker is available and connected."""
        if not self.connected:
            # Try reconnecting once per check if disconnected
            return self.connect()
        return True

    def get_containers(self) -> List[Dict[str, Any]]:
        """Get a list of all containers with basic stats."""
        if not self.is_available():
            return []

        containers_data = []
        try:
            # List all containers (running and stopped)
            containers = self.client.containers.list(all=True)
            
            for c in containers:
                # Basic info is fast
                info = {
                    "id": c.short_id,
                    "name": c.name,
                    "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                    "status": c.status,
                    "state": c.attrs.get("State", {}).get("Status", "unknown"),
                    "cpu_percent": 0.0, # stats are expensive, fetched separately or on demand
                    "mem_usage": 0,
                    "mem_limit": 0,
                }
                containers_data.append(info)
                
        except (DockerException, APIError):
            self.connected = False
            
        return containers_data

    def get_container_stats(self, container_id: str) -> Dict[str, float]:
        """Fetch real-time stats for a specific container.
        
        Note: This can be slow if called for many containers.
        """
        if not self.is_available():
            return {"cpu": 0.0, "mem": 0.0, "mem_limit": 0.0}

        try:
            c = self.client.containers.get(container_id)
            if c.status != 'running':
                return {"cpu": 0.0, "mem": 0.0, "mem_limit": 0.0}
                
            stats = c.stats(stream=False)
            
            # Calculate CPU
            # https://docs.docker.com/engine/api/v1.41/#operation/ContainerStats
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                        stats['precpu_stats']['cpu_usage']['total_usage']
            system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - \
                               stats['precpu_stats']['system_cpu_usage']
            number_cpus = stats['cpu_stats']['online_cpus']
            
            cpu_percent = 0.0
            if system_cpu_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_cpu_delta) * number_cpus * 100.0
                
            # Calculate Memory
            mem_usage = stats['memory_stats']['usage']
            mem_limit = stats['memory_stats']['limit']
            
            return {
                "cpu": cpu_percent,
                "mem": mem_usage,
                "mem_limit": mem_limit
            }

        except Exception:
            return {"cpu": 0.0, "mem": 0.0, "mem_limit": 0.0}

    def stop_container(self, container_id: str) -> bool:
        if not self.is_available(): return False
        try:
            self.client.containers.get(container_id).stop()
            return True
        except: return False

    def start_container(self, container_id: str) -> bool:
        if not self.is_available(): return False
        try:
            self.client.containers.get(container_id).start()
            return True
        except: return False

    def restart_container(self, container_id: str) -> bool:
        if not self.is_available(): return False
        try:
            self.client.containers.get(container_id).restart()
            return True
        except: return False

"""
Pulse Container API - interface to the Docker engine.

Docker is an optional extra (``pip install pulse-monitor[docker]``). Access to
the Docker socket is equivalent to root on the host, so this module connects
lazily - only when the Docker panel is first shown - and never on import or at
app startup. Failed connections back off instead of retrying every frame.
"""
import time
from typing import Any, Dict, List, Optional

from pulse.actions import ActionResult

try:
    import docker
    from docker.errors import APIError, DockerException
    HAS_DOCKER = True
except ImportError:  # pragma: no cover - depends on the optional extra
    HAS_DOCKER = False

    class DockerException(Exception):
        """Placeholder so except clauses stay valid without the extra."""

    class APIError(DockerException):
        """Placeholder so except clauses stay valid without the extra."""


INSTALL_HINT = "Docker support not installed. Run: pip install pulse-monitor[docker]"

# How long to wait after a failed connection before trying again. Without this
# the panel retried on every refresh, blocking the UI on socket timeouts.
_RECONNECT_BACKOFF = 15.0


class ContainerController:
    """Controller for Docker container operations."""

    def __init__(self) -> None:
        self.client = None
        self.connected = False
        self.last_error: Optional[str] = None if HAS_DOCKER else INSTALL_HINT
        self._next_attempt = 0.0

    @property
    def available(self) -> bool:
        """True if the docker package is installed at all."""
        return HAS_DOCKER

    def connect(self) -> bool:
        """Try to reach the Docker daemon, honouring the backoff window."""
        if not HAS_DOCKER:
            return False

        now = time.monotonic()
        if now < self._next_attempt:
            return False

        try:
            self.client = docker.from_env()
            self.client.ping()
            self.connected = True
            self.last_error = None
            return True
        except (DockerException, APIError, OSError) as exc:
            self.client = None
            self.connected = False
            self.last_error = str(exc).strip() or "Docker daemon unreachable"
            self._next_attempt = now + _RECONNECT_BACKOFF
            return False

    def is_available(self) -> bool:
        """Check whether the daemon is reachable, reconnecting if it is time to."""
        if self.connected:
            return True
        return self.connect()

    def status_text(self) -> str:
        """A short explanation of why the panel has nothing to show."""
        if not HAS_DOCKER:
            return INSTALL_HINT
        if not self.connected:
            return "Docker daemon\nNOT REACHABLE"
        return "Docker connected"

    def get_containers(self) -> List[Dict[str, Any]]:
        """Get a list of all containers with basic info."""
        if not self.is_available():
            return []

        containers_data: List[Dict[str, Any]] = []
        try:
            for container in self.client.containers.list(all=True):
                image = container.image
                tags = getattr(image, "tags", [])
                containers_data.append({
                    "id": container.short_id,
                    "name": container.name,
                    "image": tags[0] if tags else str(getattr(image, "id", ""))[:12],
                    "status": container.status,
                    "state": container.attrs.get("State", {}).get("Status", "unknown"),
                })
        except (DockerException, APIError, OSError) as exc:
            self.connected = False
            self.last_error = str(exc).strip() or "Docker daemon unreachable"
            self._next_attempt = time.monotonic() + _RECONNECT_BACKOFF

        return containers_data

    def get_container_stats(self, container_id: str) -> Dict[str, float]:
        """Fetch real-time stats for one container.

        This is a blocking round trip to the daemon - do not call it for every
        container on every refresh.
        """
        empty = {"cpu": 0.0, "mem": 0.0, "mem_limit": 0.0}
        if not self.is_available():
            return empty

        try:
            container = self.client.containers.get(container_id)
            if container.status != "running":
                return empty

            stats = container.stats(stream=False)

            cpu_delta = (stats["cpu_stats"]["cpu_usage"]["total_usage"]
                         - stats["precpu_stats"]["cpu_usage"]["total_usage"])
            system_delta = (stats["cpu_stats"]["system_cpu_usage"]
                            - stats["precpu_stats"]["system_cpu_usage"])
            online_cpus = stats["cpu_stats"].get("online_cpus", 1)

            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0

            return {
                "cpu": cpu_percent,
                "mem": stats["memory_stats"].get("usage", 0),
                "mem_limit": stats["memory_stats"].get("limit", 0),
            }
        except (DockerException, APIError, KeyError, OSError):
            return empty

    # ------------------------------------------------------------------
    # State-changing operations. Callers must confirm with the user first.
    # ------------------------------------------------------------------
    def _operate(self, operation: str, container_id: str) -> ActionResult:
        if not HAS_DOCKER:
            return ActionResult(False, INSTALL_HINT)
        if not self.is_available():
            return ActionResult(False, self.last_error or "Docker daemon unreachable")

        try:
            container = self.client.containers.get(container_id)
            name = container.name
            getattr(container, operation)()
        except (DockerException, APIError, OSError) as exc:
            detail = str(exc).strip() or "unknown error"
            return ActionResult(False, f"Could not {operation} {container_id}: {detail}")

        return ActionResult(True, f"Container {name} {operation}ped."
                            if operation == "stop"
                            else f"Container {name} {operation}ed.")

    def stop_container(self, container_id: str) -> ActionResult:
        return self._operate("stop", container_id)

    def start_container(self, container_id: str) -> ActionResult:
        return self._operate("start", container_id)

    def restart_container(self, container_id: str) -> ActionResult:
        return self._operate("restart", container_id)

"""
Pulse Aether - Main Visualization Engine

Orchestrates the render loop, combining shapes, renderer,
and system metrics to produce animated ASCII frames.
"""
import time
import math
import psutil
from typing import Optional
from collections import deque

from pulse.aether.shapes import (
    get_cube_vertices, get_cube_edges,
    get_octahedron_vertices, get_octahedron_edges,
    rotate_shape, apply_jitter,
)
from pulse.aether.renderer import AetherRenderer
from pulse.aether.terrain import TerrainRenderer, FluxRenderer


class AetherEngine:
    """
    The main Aether visualization engine.
    
    Manages state for the Monolith, Terrain, and Flux, and orchestrates
    frame generation based on system metrics.
    """
    
    def __init__(self, width: int = 80, height: int = 24):
        """Initialize the engine with canvas dimensions."""
        self.width = width
        self.height = height
        self.renderer = AetherRenderer(width, height)
        
        # Visual pillar renderers
        self.terrain = TerrainRenderer(width, height)
        self.flux = FluxRenderer(width, height)
        
        # Rotation state (in radians)
        self.angle_x = 0.0
        self.angle_y = 0.0
        self.angle_z = 0.0
        
        # Base rotation speed (radians per frame)
        self.base_rotation_speed = 0.03
        
        # Shape selection - USE CUBE
        self.use_octahedron = False
        
        # Metric history for terrain (last 60 samples)
        self.cpu_history: deque = deque(maxlen=60)
        self.mem_history: deque = deque(maxlen=60)
        
        # Network/Disk I/O tracking for Flux
        self._last_net_io = None
        self._last_disk_io = None
        self.io_intensity = 0.0
        
        # Cached metrics for HUD
        self._current_cpu = 0.0
        self._current_mem = 0.0
        self._current_io = 0.0
        
        # Atmosphere (breathing) state
        self.breath_phase = 0.0
        self.breath_speed = 0.08
        
        # Performance tracking
        self.last_frame_time = 0.0
        self.target_fps = 15  # Slightly lower for stability
        self.frame_duration = 1.0 / self.target_fps
    
    def resize(self, width: int, height: int):
        """Resize the rendering canvas."""
        self.width = width
        self.height = height
        self.renderer.resize(width, height)
        self.terrain = TerrainRenderer(width, height)
        self.flux = FluxRenderer(width, height)
    
    def _get_metrics(self) -> dict:
        """Fetch current system metrics."""
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            
            # Cache for HUD
            self._current_cpu = cpu
            self._current_mem = mem
            
            # Store history
            self.cpu_history.append(cpu)
            self.mem_history.append(mem)
            
            # Calculate I/O intensity for Flux
            try:
                net = psutil.net_io_counters()
                disk = psutil.disk_io_counters()
                
                if self._last_net_io and self._last_disk_io:
                    net_delta = (net.bytes_sent - self._last_net_io.bytes_sent +
                                 net.bytes_recv - self._last_net_io.bytes_recv)
                    disk_delta = (disk.read_bytes - self._last_disk_io.read_bytes +
                                  disk.write_bytes - self._last_disk_io.write_bytes)
                    
                    io_total = net_delta + disk_delta
                    self.io_intensity = min(1.0, io_total / (50 * 1024 * 1024))
                    self._current_io = self.io_intensity
                
                self._last_net_io = net
                self._last_disk_io = disk
            except Exception:
                self.io_intensity = 0.0
            
            return {
                'cpu': cpu,
                'mem': mem,
                'cpu_intensity': cpu / 100.0,
                'mem_intensity': mem / 100.0,
                'io_intensity': self.io_intensity,
            }
        except Exception:
            return {'cpu': 0, 'mem': 0, 'cpu_intensity': 0, 'mem_intensity': 0, 'io_intensity': 0}
    
    def _draw_hud(self, metrics: dict):
        """Draw telemetry HUD overlays on the buffer."""
        buf = self.renderer.buffer
        w = self.width
        h = len(buf)
        
        # === TOP-LEFT: System Status ===
        cpu = metrics['cpu']
        mem = metrics['mem']
        status = "NOMINAL" if cpu < 50 else "ELEVATED" if cpu < 80 else "CRITICAL"
        
        # Status indicator
        if h > 0 and w > 30:
            line1 = f"┌─ AETHER ─────────────┐"
            line2 = f"│ STATUS: {status:8s}    │"
            line3 = f"│ CPU: {cpu:5.1f}%          │"
            line4 = f"│ MEM: {mem:5.1f}%          │"
            line5 = f"└──────────────────────┘"
            
            for i, line in enumerate([line1, line2, line3, line4, line5]):
                if i < h:
                    for j, char in enumerate(line):
                        if j < w:
                            buf[i][j] = char
        
        # === BOTTOM: Real-time metrics bar ===
        if h > 2:
            # CPU bar
            cpu_bar_width = min(20, w // 4)
            cpu_filled = int((cpu / 100.0) * cpu_bar_width)
            cpu_bar = "█" * cpu_filled + "░" * (cpu_bar_width - cpu_filled)
            
            # MEM bar
            mem_filled = int((mem / 100.0) * cpu_bar_width)
            mem_bar = "█" * mem_filled + "░" * (cpu_bar_width - mem_filled)
            
            bottom_line = f" CPU [{cpu_bar}] {cpu:5.1f}%   MEM [{mem_bar}] {mem:5.1f}%"
            
            y = h - 1
            for j, char in enumerate(bottom_line):
                if j < w:
                    buf[y][j] = char
    
    def render_frame(self) -> str:
        """
        Generate a single frame of the Aether visualization.
        
        Returns the ASCII string representation.
        """
        # Frame rate limiting
        now = time.time()
        elapsed = now - self.last_frame_time
        if elapsed < self.frame_duration:
            return self.renderer.get_frame()
        self.last_frame_time = now
        
        # Get current metrics
        metrics = self._get_metrics()
        
        # Clear the canvas
        self.renderer.clear()
        
        # === 1. TERRAIN (Background layer) ===
        self.terrain.render(
            self.renderer.buffer, 
            self.cpu_history, 
            metrics['cpu_intensity']
        )
        
        # === 2. FLUX (Particle layer) ===
        self.flux.set_intensity(metrics['io_intensity'])
        self.flux.update()
        self.flux.render(self.renderer.buffer)
        
        # === 3. MONOLITH (Foreground layer - CUBE) ===
        vertices = get_cube_vertices(scale=1.1)
        edges = get_cube_edges()
        
        # Calculate rotation speed based on CPU load
        speed_multiplier = 1.0 + (metrics['cpu_intensity'] * 2.0)
        
        # Update rotation angles
        self.angle_x += self.base_rotation_speed * speed_multiplier * 0.5
        self.angle_y += self.base_rotation_speed * speed_multiplier
        self.angle_z += self.base_rotation_speed * speed_multiplier * 0.2
        
        # Apply rotation
        rotated = rotate_shape(vertices, self.angle_x, self.angle_y, self.angle_z)
        
        # Apply stress jitter at high CPU
        if metrics['cpu_intensity'] > 0.7:
            jitter_intensity = (metrics['cpu_intensity'] - 0.7) / 0.3
            rotated = apply_jitter(rotated, jitter_intensity * 0.5)
        
        # Render the wireframe
        self.renderer.render_wireframe(rotated, edges)
        
        # === 4. HUD OVERLAY ===
        self._draw_hud(metrics)
        
        # === 5. ATMOSPHERE (Breathing phase) ===
        self.breath_phase += self.breath_speed * (1.0 + metrics['cpu_intensity'])
        
        return self.renderer.get_frame()
    
    def get_status_line(self) -> str:
        """Return a minimal status line for overlay."""
        if self.cpu_history:
            cpu = self.cpu_history[-1]
            status = "NOMINAL" if cpu < 50 else "ELEVATED" if cpu < 80 else "CRITICAL"
            return f"[ AETHER · {status} ]"
        return "[ AETHER · INITIALIZING ]"
    
    def get_atmosphere_char(self) -> str:
        """Return a breathing indicator character."""
        chars = ['○', '◎', '●', '◉', '◎']
        idx = int((math.sin(self.breath_phase) + 1.0) / 2.0 * (len(chars) - 1))
        return chars[idx]

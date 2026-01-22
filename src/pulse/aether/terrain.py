"""
Pulse Aether - Terrain Renderer

Renders a scrolling perspective grid that represents
system history as a 3D "terrain" landscape.
"""
from typing import List
from collections import deque


class TerrainRenderer:
    """
    Renders a perspective grid terrain at the bottom of the screen.
    The height of grid points is driven by historical CPU/Memory data.
    """
    
    def __init__(self, width: int, height: int):
        """Initialize terrain with canvas dimensions."""
        self.width = width
        self.height = height
        
        # Terrain occupies bottom portion of screen
        self.terrain_height = height // 3
        self.terrain_start_y = height - self.terrain_height
        
        # Grid parameters
        self.grid_depth = 12  # Number of horizontal lines into the distance
        self.grid_cols = 20  # Number of vertical lines
        
        # Scroll offset (for animation)
        self.scroll_offset = 0.0
        self.scroll_speed = 0.3
        
        # ASCII chars for terrain
        self.grid_char = '·'
        self.peak_char = '▲'
        self.ridge_char = '░'
    
    def render(self, buffer: List[List[str]], history: deque, intensity: float = 0.0):
        """
        Render the terrain onto the buffer.
        
        Args:
            buffer: The 2D character buffer to draw on
            history: CPU history (deque of float 0-100)
            intensity: Current load intensity (0.0-1.0) for scroll speed
        """
        if not history:
            return
        
        # Update scroll
        self.scroll_offset += self.scroll_speed * (1.0 + intensity * 2.0)
        if self.scroll_offset >= 1.0:
            self.scroll_offset -= 1.0
        
        # Convert history to list for indexing
        hist_list = list(history)
        
        # Draw horizontal grid lines (perspective effect)
        for row_idx in range(self.grid_depth):
            # Calculate Y position with perspective (closer = lower on screen)
            perspective_factor = (row_idx + 1) / self.grid_depth
            y = self.terrain_start_y + int((1.0 - perspective_factor) * self.terrain_height * 0.8)
            
            if y >= len(buffer):
                continue
            
            # Calculate width at this depth (narrower further away)
            row_width = int(self.width * perspective_factor)
            start_x = (self.width - row_width) // 2
            
            # Get history value for this row
            hist_idx = min(row_idx, len(hist_list) - 1) if hist_list else 0
            hist_value = hist_list[-(hist_idx + 1)] if hist_list else 0
            
            # Calculate height offset based on history
            height_offset = int((hist_value / 100.0) * 4)  # Max 4 chars up
            adjusted_y = max(0, y - height_offset)
            
            # Draw the grid line
            for x in range(start_x, start_x + row_width):
                if 0 <= x < self.width and 0 <= adjusted_y < len(buffer):
                    # Vary character based on height
                    if height_offset >= 3:
                        char = self.peak_char
                    elif height_offset >= 1:
                        char = self.ridge_char
                    else:
                        char = self.grid_char
                    
                    # Only draw if cell is empty
                    if buffer[adjusted_y][x] == ' ':
                        buffer[adjusted_y][x] = char


class FluxRenderer:
    """
    Renders particle streams flowing from screen edges toward the center.
    Represents Network/Disk I/O activity.
    """
    
    PARTICLE_CHARS = ['·', '∙', '•', '*', '✦']
    
    def __init__(self, width: int, height: int):
        """Initialize flux with canvas dimensions."""
        self.width = width
        self.height = height
        
        # Particles: list of (x, y, velocity_x, velocity_y, char_idx)
        self.particles: List[List[float]] = []
        
        # Center target
        self.center_x = width // 2
        self.center_y = height // 2
        
        # Spawn settings
        self.max_particles = 30
        self.spawn_rate = 0.0  # Particles per frame (driven by I/O)
    
    def set_intensity(self, io_intensity: float):
        """Set spawn rate based on I/O intensity (0.0-1.0)."""
        self.spawn_rate = io_intensity * 3.0  # Up to 3 particles per frame
    
    def update(self):
        """Update particle positions and spawn new ones."""
        import random
        
        # Spawn new particles at edges
        while len(self.particles) < self.max_particles and random.random() < self.spawn_rate:
            # Random edge spawn
            edge = random.choice(['top', 'bottom', 'left', 'right'])
            if edge == 'top':
                x, y = random.randint(0, self.width - 1), 0
            elif edge == 'bottom':
                x, y = random.randint(0, self.width - 1), self.height - 1
            elif edge == 'left':
                x, y = 0, random.randint(0, self.height - 1)
            else:
                x, y = self.width - 1, random.randint(0, self.height - 1)
            
            # Velocity toward center
            dx = (self.center_x - x) * 0.1
            dy = (self.center_y - y) * 0.1
            
            char_idx = random.randint(0, len(self.PARTICLE_CHARS) - 1)
            self.particles.append([float(x), float(y), dx, dy, char_idx])
        
        # Move particles
        new_particles = []
        for p in self.particles:
            p[0] += p[2]  # x += vx
            p[1] += p[3]  # y += vy
            
            # Remove if near center or off-screen
            dist_to_center = ((p[0] - self.center_x) ** 2 + (p[1] - self.center_y) ** 2) ** 0.5
            if dist_to_center > 2 and 0 <= p[0] < self.width and 0 <= p[1] < self.height:
                new_particles.append(p)
        
        self.particles = new_particles
    
    def render(self, buffer: List[List[str]]):
        """Render particles onto the buffer."""
        for p in self.particles:
            x, y = int(p[0]), int(p[1])
            char_idx = int(p[4])
            if 0 <= x < self.width and 0 <= y < len(buffer):
                if buffer[y][x] == ' ':
                    buffer[y][x] = self.PARTICLE_CHARS[char_idx]

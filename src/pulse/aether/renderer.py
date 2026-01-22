"""
Pulse Aether - 2D Projection and ASCII Rendering

Projects 3D coordinates onto a 2D character grid and
selects appropriate ASCII characters for wireframe edges.
"""
from typing import List, Tuple, Optional
from pulse.aether.shapes import Vertex, Edge

# ASCII characters for drawing edges based on angle
# Horizontal, Vertical, and Diagonals
EDGE_CHARS = {
    'horizontal': '─',
    'vertical': '│',
    'diag_up': '/',
    'diag_down': '\\',
    'cross': '+',
    'node': '●',
}


class AetherRenderer:
    """
    Renders 3D shapes to a 2D ASCII character buffer.
    """
    
    def __init__(self, width: int, height: int):
        """Initialize with canvas dimensions."""
        self.width = width
        self.height = height
        self.fov = 60  # Field of view in degrees
        self.camera_distance = 4.0  # Distance from origin
        
        # Pre-allocate the character buffer (will be reused each frame)
        self.buffer: List[List[str]] = []
        self.clear()
    
    def clear(self):
        """Clear the buffer to empty space."""
        self.buffer = [[' ' for _ in range(self.width)] for _ in range(self.height)]
    
    def resize(self, width: int, height: int):
        """Resize the canvas."""
        self.width = width
        self.height = height
        self.clear()
    
    def project(self, vertex: Vertex) -> Optional[Tuple[int, int]]:
        """
        Project a 3D vertex to 2D screen coordinates.
        Returns None if the point is behind the camera.
        """
        x, y, z = vertex
        
        # Simple perspective projection
        # Move camera back along Z axis
        z_offset = z + self.camera_distance
        
        if z_offset <= 0.1:  # Behind camera
            return None
        
        # Perspective divide
        scale = self.fov / z_offset
        
        # Convert to screen coordinates (center of screen is origin)
        screen_x = int(self.width / 2 + x * scale * 2)  # *2 for aspect ratio
        screen_y = int(self.height / 2 - y * scale)  # Y is inverted
        
        return (screen_x, screen_y)
    
    def draw_point(self, x: int, y: int, char: str = '●'):
        """Draw a single character at the given position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y][x] = char
    
    def draw_line(self, x0: int, y0: int, x1: int, y1: int, char: Optional[str] = None):
        """
        Draw a line between two points using Bresenham's algorithm.
        Auto-selects character based on line angle if char is None.
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        # Select character based on slope
        if char is None:
            if dx == 0:
                char = EDGE_CHARS['vertical']
            elif dy == 0:
                char = EDGE_CHARS['horizontal']
            elif (x1 > x0) == (y1 > y0):
                char = EDGE_CHARS['diag_down']
            else:
                char = EDGE_CHARS['diag_up']
        
        # Bresenham's line algorithm
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        
        if dx > dy:
            err = dx / 2
            y = y0
            for x in range(x0, x1 + sx, sx):
                self.draw_point(x, y, char)
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
        else:
            err = dy / 2
            x = x0
            for y in range(y0, y1 + sy, sy):
                self.draw_point(x, y, char)
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
    
    def render_wireframe(self, vertices: List[Vertex], edges: List[Edge]):
        """
        Render a 3D wireframe shape to the buffer.
        """
        # Project all vertices to 2D
        projected = [self.project(v) for v in vertices]
        
        # Draw edges
        for v1_idx, v2_idx in edges:
            p1 = projected[v1_idx]
            p2 = projected[v2_idx]
            
            if p1 is not None and p2 is not None:
                self.draw_line(p1[0], p1[1], p2[0], p2[1])
        
        # Draw vertices as nodes (on top of edges)
        for p in projected:
            if p is not None:
                self.draw_point(p[0], p[1], EDGE_CHARS['node'])
    
    def get_frame(self) -> str:
        """Return the current buffer as a single string."""
        return '\n'.join(''.join(row) for row in self.buffer)

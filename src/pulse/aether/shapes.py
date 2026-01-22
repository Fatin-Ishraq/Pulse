"""
Pulse Aether - 3D Shapes and Transformations

Provides vertex definitions and rotation matrix math for
rendering 3D wireframes in ASCII.
"""
import math
from typing import List, Tuple

# Type aliases for clarity
Vertex = Tuple[float, float, float]
Edge = Tuple[int, int]  # Indices into vertex list


# =============================================================================
# SHAPE DEFINITIONS (Vertices and Edges)
# =============================================================================

def get_cube_vertices(scale: float = 1.0) -> List[Vertex]:
    """Return the 8 vertices of a cube centered at origin."""
    s = scale
    return [
        (-s, -s, -s), ( s, -s, -s), ( s,  s, -s), (-s,  s, -s),  # Back face
        (-s, -s,  s), ( s, -s,  s), ( s,  s,  s), (-s,  s,  s),  # Front face
    ]

def get_cube_edges() -> List[Edge]:
    """Return the 12 edges of a cube as vertex index pairs."""
    return [
        # Back face
        (0, 1), (1, 2), (2, 3), (3, 0),
        # Front face
        (4, 5), (5, 6), (6, 7), (7, 4),
        # Connecting edges
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]

def get_octahedron_vertices(scale: float = 1.0) -> List[Vertex]:
    """Return the 6 vertices of an octahedron centered at origin."""
    s = scale
    return [
        ( 0,  s,  0),  # Top
        ( 0, -s,  0),  # Bottom
        ( s,  0,  0),  # Right
        (-s,  0,  0),  # Left
        ( 0,  0,  s),  # Front
        ( 0,  0, -s),  # Back
    ]

def get_octahedron_edges() -> List[Edge]:
    """Return the 12 edges of an octahedron."""
    return [
        # Top pyramid
        (0, 2), (0, 3), (0, 4), (0, 5),
        # Bottom pyramid
        (1, 2), (1, 3), (1, 4), (1, 5),
        # Equator
        (2, 4), (4, 3), (3, 5), (5, 2),
    ]


# =============================================================================
# ROTATION MATRICES
# =============================================================================

def rotate_x(vertex: Vertex, angle: float) -> Vertex:
    """Rotate a vertex around the X axis."""
    x, y, z = vertex
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (x, y * cos_a - z * sin_a, y * sin_a + z * cos_a)

def rotate_y(vertex: Vertex, angle: float) -> Vertex:
    """Rotate a vertex around the Y axis."""
    x, y, z = vertex
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (x * cos_a + z * sin_a, y, -x * sin_a + z * cos_a)

def rotate_z(vertex: Vertex, angle: float) -> Vertex:
    """Rotate a vertex around the Z axis."""
    x, y, z = vertex
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a, z)


def rotate_vertex(vertex: Vertex, angle_x: float, angle_y: float, angle_z: float) -> Vertex:
    """Apply XYZ rotation to a single vertex."""
    v = rotate_x(vertex, angle_x)
    v = rotate_y(v, angle_y)
    v = rotate_z(v, angle_z)
    return v


def rotate_shape(vertices: List[Vertex], angle_x: float, angle_y: float, angle_z: float) -> List[Vertex]:
    """Rotate all vertices of a shape."""
    return [rotate_vertex(v, angle_x, angle_y, angle_z) for v in vertices]


# =============================================================================
# JITTER / GLITCH EFFECT
# =============================================================================

def apply_jitter(vertices: List[Vertex], intensity: float) -> List[Vertex]:
    """
    Apply random jitter to vertices based on intensity (0.0 - 1.0).
    Used to simulate "stress" on the shape when CPU is high.
    """
    import random
    if intensity <= 0:
        return vertices
    
    jittered = []
    for x, y, z in vertices:
        jitter_amount = intensity * 0.3  # Max 30% displacement
        dx = random.uniform(-jitter_amount, jitter_amount)
        dy = random.uniform(-jitter_amount, jitter_amount)
        dz = random.uniform(-jitter_amount, jitter_amount)
        jittered.append((x + dx, y + dy, z + dz))
    return jittered

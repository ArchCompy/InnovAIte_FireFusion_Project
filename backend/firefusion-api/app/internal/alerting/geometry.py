"""Planar polygon intersection for matching forecast polygons to a region.

Pure Python on purpose: forecast polygons are small, and this avoids adding a
geometry dependency to the service image. Coordinates are [longitude,
latitude] and are treated as planar, which is accurate enough at the scale of
a forecast cell.

Boundaries count as inside. For an emergency tool, a region that merely touches
a high-risk polygon is treated as affected: a missed alert is worse than an
extra one.

A polygon is a list of rings: the exterior first, then any holes, as in
GeoJSON.
"""
from typing import Sequence

Position = Sequence[float]
Ring = Sequence[Position]
Polygon = Sequence[Ring]

INSIDE = 1
BOUNDARY = 0
OUTSIDE = -1


def _cross(o: Position, a: Position, b: Position) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_segment(p: Position, a: Position, b: Position) -> bool:
    """True if p lies on segment ab, given that p is collinear with it."""
    return (
        min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
    )


def segments_intersect(a: Position, b: Position, c: Position, d: Position) -> bool:
    """True if segment ab and segment cd share at least one point."""
    d1 = _cross(c, d, a)
    d2 = _cross(c, d, b)
    d3 = _cross(a, b, c)
    d4 = _cross(a, b, d)

    if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
        return True

    # Touching or collinear overlap.
    if d1 == 0 and _on_segment(a, c, d):
        return True
    if d2 == 0 and _on_segment(b, c, d):
        return True
    if d3 == 0 and _on_segment(c, a, b):
        return True
    if d4 == 0 and _on_segment(d, a, b):
        return True
    return False


def locate_in_ring(point: Position, ring: Ring) -> int:
    """Return INSIDE, BOUNDARY or OUTSIDE for a point against one closed ring."""
    inside = False
    for i in range(len(ring) - 1):
        a, b = ring[i], ring[i + 1]

        if _cross(a, b, point) == 0 and _on_segment(point, a, b):
            return BOUNDARY

        # Ray cast to the right; count edges that straddle the point's latitude.
        if (a[1] > point[1]) != (b[1] > point[1]):
            x_at_y = a[0] + (point[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if point[0] < x_at_y:
                inside = not inside

    return INSIDE if inside else OUTSIDE


def point_in_polygon(point: Position, polygon: Polygon) -> bool:
    """True if the point is in the polygon's material (boundary included).

    A point strictly inside a hole is outside the polygon; a point on a hole's
    edge is on the polygon's edge, so it counts as inside.
    """
    if locate_in_ring(point, polygon[0]) == OUTSIDE:
        return False
    return all(locate_in_ring(point, hole) != INSIDE for hole in polygon[1:])


def _bounds(polygon: Polygon) -> tuple[float, float, float, float]:
    xs = [p[0] for p in polygon[0]]
    ys = [p[1] for p in polygon[0]]
    return min(xs), min(ys), max(xs), max(ys)


def _rings_cross(a: Polygon, b: Polygon) -> bool:
    for ring_a in a:
        for i in range(len(ring_a) - 1):
            for ring_b in b:
                for j in range(len(ring_b) - 1):
                    if segments_intersect(
                        ring_a[i], ring_a[i + 1], ring_b[j], ring_b[j + 1]
                    ):
                        return True
    return False


def polygons_intersect(a: Polygon, b: Polygon) -> bool:
    """True if the two polygons share any area or boundary point."""
    a_min_x, a_min_y, a_max_x, a_max_y = _bounds(a)
    b_min_x, b_min_y, b_max_x, b_max_y = _bounds(b)
    if a_max_x < b_min_x or b_max_x < a_min_x or a_max_y < b_min_y or b_max_y < a_min_y:
        return False

    # Any two ring edges meeting means the polygons overlap or touch.
    if _rings_cross(a, b):
        return True

    # No edges meet, so the polygons are either disjoint or one is nested in
    # the other's material (a hole makes "nested" not the same as "enclosed").
    return point_in_polygon(a[0][0], b) or point_in_polygon(b[0][0], a)

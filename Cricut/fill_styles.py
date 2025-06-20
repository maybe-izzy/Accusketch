import numpy as np
from svgpathtools import Path, Line
import numpy as np
from math import cos, sin, radians, hypot


def vertical(path, spacing, angle_deg=45, overshoot=2.0):
    # translate to origin
    xmin, xmax, ymin, ymax = path.bbox()
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    center = complex(cx, cy)
    p_local = path.translated(-center)

    # unit vectors: direction (v̂), step (n̂)
    θ = radians(angle_deg)
    v̂ = complex(cos(θ),  sin(θ))   # along the hatch
    n̂ = complex(-sin(θ), cos(θ))   # perpendicular

    # range of projections of bbox corners onto n̂ 
    corners = [complex(x - cx, y - cy) for x in (xmin, xmax) for y in (ymin, ymax)]
    d_vals = [c.real*n̂.real + c.imag*n̂.imag for c in corners]
    d_min, d_max = min(d_vals), max(d_vals)

    # compute safe half length for hatch segment
    diag = hypot(xmax - xmin, ymax - ymin)
    half_len = max(overshoot * diag, spacing * 5)

    # sweep hatch lines over path 
    hatch_lines = []
    for d in np.arange(d_min - spacing, d_max + spacing, spacing):
        p0 = d * n̂
        hatch = Line(start = p0 - v̂ * half_len, end = p0 + v̂ * half_len)

        # get intersections
        hits = []
        for seg in p_local:
            # if segment length is 0, skip it 
            if seg.start == seg.end: 
                continue
            for t_seg, _ in seg.intersect(hatch):
                hits.append(seg.point(t_seg))
        if not hits:
            continue

        # order hits along hatch and connect interior pairs
        hits.sort(key = lambda p: p.real * v̂.real + p.imag * v̂.imag)
        for i in range(0, len(hits) - 1, 2):
            hatch_lines.append(Line(start = hits[i] + center, end = hits[i + 1] + center))

    return hatch_lines

def vertical_crosshatch(path, spacing, angles, overshoot=2.0):
    all_hatches = []

    for ang in angles:
        pass_hatches = vertical(path, spacing, ang, overshoot)
        all_hatches.extend(pass_hatches)

    return all_hatches

def zigzag(path, spacing, layers=2):
    xmin, xmax, ymin, ymax = path.bbox()
    x_values = np.arange(xmin, xmax + spacing, spacing)

    pairs = []
    for x in x_values:
        line = Line(complex(x, ymin - 10), complex(x, ymax + 10))
        pts = [seg.point(t1) for seg in path for t1, _ in seg.intersect(line)]
        pts.sort(key=lambda p: p.imag)
        for i in range(0, len(pts) - 1, 2):
            pairs.append((pts[i], pts[i + 1]))

    if not pairs:
        return None

    points = [pt for pair in pairs for pt in pair]
    full = points[:]
    for i in range(1, layers):
        full += reversed(points) if i % 2 else points

    return Path(*[Line(full[i], full[i+1]) for i in range(len(full) - 1)])

def crosshatch(path, spacing, layers=2):
    print("trc: hatch_fill_crosshatch")

    # --- Helper for one zigzag direction ---
    def build_zigzag_along_axis(axis='vertical'):
        print("trc: build_zigzag_along_axis")

        coords = []

        if axis == 'vertical':
            x_values = np.arange(xmin, xmax + spacing, spacing)
            for x in x_values:
                intersections = []
                vertical_line = Line(start=complex(x, ymin - 10), end=complex(x, ymax + 10))
                for segment in path:
                    pts = segment.intersect(vertical_line)
                    for t1, _ in pts:
                        point = segment.point(t1)
                        intersections.append(point)
                intersections.sort(key=lambda p: p.imag)
                for i in range(0, len(intersections) - 1, 2):
                    bottom = intersections[i + 1]
                    top = intersections[i]
                    coords.append((bottom, top))
        else:  # axis == 'horizontal'
            y_values = np.arange(ymin, ymax + spacing, spacing)
            for y in y_values:
                intersections = []
                horizontal_line = Line(start=complex(xmin - 10, y), end=complex(xmax + 10, y))
                for segment in path:
                    pts = segment.intersect(horizontal_line)
                    for t1, _ in pts:
                        point = segment.point(t1)
                        intersections.append(point)
                intersections.sort(key=lambda p: p.real)
                for i in range(0, len(intersections) - 1, 2):
                    left = intersections[i]
                    right = intersections[i + 1]
                    coords.append((left, right))

        if not coords:
            return []

        # Flatten to alternating zigzag line segments
        points = []
        for a, b in coords:
            points.append(a)
            points.append(b)

        all_points = list(points)
        for i in range(1, layers):
            if i % 2 == 1:
                all_points += list(reversed(points))
            else:
                all_points += list(points)

        return all_points

    # --- Step 1: Get bounds ---
    xmin, xmax, ymin, ymax = path.bbox()

    # --- Step 2: Build first zigzag (vertical) ---
    vertical_points = build_zigzag_along_axis('vertical')
    segments = []
    last_point = vertical_points[0]
    for pt in vertical_points[1:]:
        segments.append(Line(last_point, pt))
        last_point = pt

    # --- Step 3: Connect to second zigzag (horizontal) ---
    horizontal_points = build_zigzag_along_axis('horizontal')
    if horizontal_points:
        # Draw connector between end of vertical to start of horizontal
        connector = Line(last_point, horizontal_points[0])
        segments.append(connector)
        last_point = horizontal_points[0]
        for pt in horizontal_points[1:]:
            segments.append(Line(last_point, pt))
            last_point = pt

    return Path(*segments) if segments else None


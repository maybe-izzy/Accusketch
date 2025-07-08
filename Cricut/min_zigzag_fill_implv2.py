from math import radians, cos, sin
from svgpathtools import smoothed_path, rotate  # you already have svgpathtools
import os
import numpy as np
from svgpathtools import Line, Path, svg2paths2, wsvg
from shapely.geometry import LineString, Polygon
import random

def is_small_path(path, min_area=0.5):
    points = [path.point(t / 100.0) for t in range(101)]
    coords = [(p.real, p.imag) for p in points]
    poly = Polygon(coords)
    return poly.area < min_area

def sample_path_to_polygon(path, num_samples=1000):
    points = [path.point(i / num_samples) for i in range(num_samples)]
    coords = [(pt.real, pt.imag) for pt in points]
    coords.append(coords[0])  # close the loop
    return Polygon(coords)

def shapely_polygon_to_svgpath(shapely_poly):
    """Convert a shapely Polygon exterior to svgpathtools.Path."""
    exterior_coords = list(shapely_poly.exterior.coords)
    segments = []
    for i in range(len(exterior_coords) - 1):
        start = complex(*exterior_coords[i])
        end = complex(*exterior_coords[i + 1])
        segments.append(Line(start, end))
    return Path(*segments)

def zigzag_fill(path, step=5, overshoot=10, path_buf=8, x_tolerance_epsilon=1e-2, angle_deg=45):
    θ = radians(angle_deg)

    # 🔁 Step 1: Rotate path to align zigzags with vertical lines
    rotated_path = path.rotated(-θ)

    # 🔁 Step 2: Do everything in rotated space
    points = [(seg.start.real, seg.start.imag) for seg in rotated_path]
    if len(points) < 3:
        print("SUPER SMALL")
        return None

    if points[0] != points[-1]:
        points.append(points[0])

    polygon = sample_path_to_polygon(rotated_path, num_samples=500)
    xmin, xmax, ymin, ymax = rotated_path.bbox()
    vertical_xs = np.arange(xmin, xmax + step, step)
    safe_polygon = polygon.buffer(path_buf)
    groups = []

    def intersect_path_with_line(line):
        intersections = []
        for seg in rotated_path:
            if seg.start == seg.end:
                continue
            for t, _ in seg.intersect(line):
                pt = seg.point(t)
                intersections.append(pt)
        intersections.sort(key=lambda p: p.imag)
        return list(zip(intersections[::2], intersections[1::2]))

    for x in vertical_xs:
        vertical_line = Line(complex(x, ymin - overshoot), complex(x, ymax + overshoot))
        pairs = intersect_path_with_line(vertical_line)
        if not pairs:
            continue
        for pair in pairs:
            was_matched = False
            for group in groups:
                last_pair = group[-1]
                scan_line = LineString([(last_pair[1].real, last_pair[1].imag),
                                        (pair[0].real, pair[0].imag)])
                dx = abs(pair[0].real - last_pair[1].real)
                if abs(dx - step) < x_tolerance_epsilon and safe_polygon.covers(scan_line):
                    group.append(pair)
                    was_matched = True
                    break
            if not was_matched:
                groups.append([pair])

    # 🔁 Step 3: Zigzag and rotate back
    zigzag_paths = []
    for group in groups:
        if not group:
            continue
        zigzag = Path()
        last_pair = group.pop(0)
        zigzag.append(Line(last_pair[0], last_pair[1]))

        for next_pair in group:
            zigzag.append(Line(last_pair[1], next_pair[0]))
            zigzag.append(Line(next_pair[0], next_pair[1]))
            last_pair = next_pair

        # 🔁 Rotate back each zigzag path
        zigzag_paths.append(zigzag.rotated(θ))

    return zigzag_paths

def main():
    input_path = os.path.join("../svg/input/", "swatch_square.svg")
    output_path = os.path.join("../svg/output/", "swatch_square.svg")
    paths, attributes, svg_attrs = svg2paths2(input_path)
    
    new_paths = []
    for path in paths:
        zigzags = zigzag_fill(path, step=.5, overshoot=10, path_buf=0.25, x_tolerance_epsilon=5e-1)
        if (zigzags):
            new_paths.extend(zigzags)
        else: 
            new_paths.append(path)
    # colors = [random_color() for _ in new_paths]

    seen = set()
    deduped_paths = []

    for i, path in enumerate(new_paths):
        key = tuple((seg.start.real, seg.start.imag, seg.end.real, seg.end.imag) for seg in path)
        if key not in seen:
            seen.add(key)
            deduped_paths.append(path)
        else:
            print(f"⚠️ Duplicate path removed at index {i}")

    wsvg(deduped_paths, filename="deduplicated_output.svg", stroke_widths=[0.1]*len(deduped_paths))

    half = len(new_paths) // 2

    # First half
    paths1 = new_paths[:half]


    # Second half
    paths2 = new_paths[half:]


    # Save each half
    #wsvg(paths1, filename="output_half_1.svg", stroke_widths=[0.1]*len(paths1))
    #wsvg(paths2, filename="output_half_2.svg", stroke_widths=[0.1]*len(paths2))
    wsvg(new_paths, filename=output_path, svg_attributes=svg_attrs, stroke_widths=[0.1 for _ in new_paths])
   
main()
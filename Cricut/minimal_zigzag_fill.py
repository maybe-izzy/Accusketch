import os
import numpy as np
from svgpathtools import Line, Path, svg2paths2, wsvg
from shapely.geometry import LineString, Polygon
import random

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

def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def zigzag_fill(path, step=5, overshoot=10, path_buf = 8, x_tolerance_epsilon=1e-2):
    points = [(seg.start.real, seg.start.imag) for seg in path]
    if len(points) < 3:
        return None  # Or raise an error, or skip

    # Ensure it's closed
    if points[0] != points[-1]:
        points.append(points[0])

    polygon = Polygon(points)
    """
    try:
        polygon = Polygon([(seg.start.real, seg.start.imag) for seg in path])
    except: 
        print("path too small!")
        return None
    """
    xmin, xmax, ymin, ymax = path.bbox()
    vertical_xs = np.arange(xmin, xmax + step, step)

    groups = []

    def intersect_path_with_line(line):
        intersections = []
        for seg in path:
            if seg.start == seg.end:
                continue  # Skip zero-length segments
            for t, _ in seg.intersect(line):
                pt = seg.point(t)
                intersections.append(pt)
       
        intersections.sort(key=lambda p: p.imag)
        return list(zip(intersections[::2], intersections[1::2]))  # pair them
    polygon = sample_path_to_polygon(path)
    safe_polygon = polygon.buffer(path_buf)
    safe_polygon_path_visual = shapely_polygon_to_svgpath(safe_polygon)

    """safe_polygon = polygon.buffer(path_buf)
    """

    for x in vertical_xs:
        vertical_line = Line(complex(x, ymin - overshoot), complex(x, ymax + overshoot))
        pairs = intersect_path_with_line(vertical_line)

        for pair in pairs:
            was_matched = False
            for group in groups:
                last_pair = group[-1]
                scan_line = LineString([(last_pair[1].real, last_pair[1].imag),
                                        (pair[0].real, pair[0].imag)])
                


                inter = safe_polygon.intersection(scan_line)
                dx = abs(pair[0].real - last_pair[1].real)
                """
                if inter.length / scan_line.length > 0.7:
                    group.append(pair)"""
                if abs(dx - step) < x_tolerance_epsilon and safe_polygon.covers(scan_line):
                    group.append(pair)
                    
                    was_matched = True
                    break
            
            if not was_matched:
                groups.append([pair])

    # Now create zigzag paths from the groups
    zigzag_paths = []
    print(f"Groups in path: {len(groups)}")
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
            zigzag_paths.append(zigzag)
        zigzag_paths = zigzag_paths + [safe_polygon_path_visual]
    
    return zigzag_paths

def main():
    input_path = os.path.join("../svg/input/", "b1.25_united.svg")
    output_path = os.path.join("../svg/output/", "b1.25_united.svg")
    paths, attributes, svg_attrs = svg2paths2(input_path)
    
    new_paths = []
    for path in paths:
        zigzags = zigzag_fill(path)
        if (zigzags):
            new_paths.extend(zigzag_fill(path, step=0.35, overshoot=10, path_buf=0.25, x_tolerance_epsilon=5e-1))

    colors = [random_color() for _ in new_paths]
    wsvg(new_paths, filename=output_path, svg_attributes=svg_attrs, colors=colors, stroke_widths=[0.1 for _ in new_paths])
   
main()
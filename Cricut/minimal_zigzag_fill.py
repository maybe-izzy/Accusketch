import os
import numpy as np
import math
from svgpathtools import Line, Path, svg2paths2, wsvg
from shapely.geometry import LineString, Polygon
import random

def dedupe_paths(paths):
    seen = set()
    unique = []
    for p in paths:
        # skip anything that isn't an svgpathtools.Path
        if not isinstance(p, Path):
            continue

        sig = p.d()        # e.g. "M 10,10 L 20,10 L 20,20 Z"
        if sig not in seen:
            seen.add(sig)
            unique.append(p)

    return unique




def rotate(path: Path,
           angle_deg: float,
           origin: complex | str = "center") -> Path:
    """
    Returns a *new* Path that is `angle_deg` degrees counter-clockwise
    around `origin`.

    `origin` may be:
      • a complex number (e.g. 135+42j), or  
      • the string "center" – aka the geometric centre of the path’s
        bounding box.
    """
    if isinstance(origin, str) and origin == "center":
        xmin, xmax, ymin, ymax = path.bbox()
        origin = complex((xmin + xmax) / 2, (ymin + ymax) / 2)

    theta = math.radians(angle_deg)
    return path.rotated(theta, origin=origin)


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

def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def zigzag_fill(path, step=5, overshoot=10, path_buf = 8, x_tolerance_epsilon=1e-2):
    
    points = [(seg.start.real, seg.start.imag) for seg in path]
    if len(points) < 3:
        print("SUPER SMALL")
        return None  # Or raise an error, or skip

    # Ensure it's closed
    if points[0] != points[-1]:
        points.append(points[0])

    polygon = sample_path_to_polygon(path, num_samples=10000)#Polygon(points)
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
    
    polygon = sample_path_to_polygon(path, num_samples=500)
    safe_polygon = polygon.buffer(path_buf)
    safe_polygon_path_visual = shapely_polygon_to_svgpath(safe_polygon)

    """safe_polygon = polygon.buffer(path_buf)
    """

    for x in vertical_xs:
        vertical_line = Line(complex(x, ymin - overshoot), complex(x, ymax + overshoot))
        pairs = intersect_path_with_line(vertical_line)
        if (len(pairs) == 0): 
            print("no pairs")
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
    
    if len(groups) == 0:
        print("No groups formed — adding debug sweep lines + intersections")
        zigzag_backup_paths = []
        zigzag_backup_paths.append(shapely_polygon_to_svgpath(safe_polygon))

        # Draw vertical sweep lines + intersections
        for x in vertical_xs:
            vertical_line = Line(complex(x, ymin - overshoot), complex(x, ymax + overshoot))

            # Add intersection points
            for seg in path:
                if seg.start == seg.end:
                    continue
                try:
                    for t, _ in seg.intersect(vertical_line):
                        pt = seg.point(t)
                        # Add small crosshair-style marker
                        radius = 0.25
                        horiz = Line(pt - radius, pt + radius)
                        vert = Line(pt - radius * 1j, pt + radius * 1j)
                        zigzag_backup_paths.extend([horiz, vert])
                except:
                    continue
        return zigzag_backup_paths
        
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

def rotate_path_around_center(path, angle_deg):
    from math import radians, cos, sin

    # Step 1: Get the bounding box center
    xmin, xmax, ymin, ymax = path.bbox()
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    center = complex(cx, cy)

    # Step 2: Translate path to origin
    path_centered = path.translated(-center)

    # Step 3: Rotate around origin
 
    path_rotated = path_centered.rotated(angle_deg)

    # Step 4: Translate back to original center
    return path_rotated.translated(center)
def main():
    svg_name   = "b1.25_united.svg"
    in_dir     = "../svg/input/"
    out_dir    = "../svg/output/"
    paths, attrs, svg_attrs = svg2paths2(os.path.join(in_dir, svg_name))

    new_paths = []
    angle     = 45.0

    for path in paths:
        # 1) compute center of the original path
        xmin, xmax, ymin, ymax = path.bbox()
        center = complex((xmin + xmax)/2, (ymin + ymax)/2)

        # 2) rotate original to lay your zig-zag on it
        rotated_shape = path.rotated(angle, origin=center)

        # 3) generate zig-zags on that rotated shape
        zigzags = zigzag_fill(
            path=rotated_shape,
            step=0.5,
            overshoot=10,
            path_buf=0.25,
            x_tolerance_epsilon=0.5
        )

        if zigzags:
            for zig in zigzags:
                # rotate each zigzag **back** around the same center
                back = zig.rotated(-angle, origin=center)
                new_paths.append(back)
        else:
            # no fill? just draw the original
            new_paths.append(path)

    # write out
    new_paths = dedupe_paths(new_paths)
    colors = [random_color() for _ in new_paths]
    wsvg(new_paths,
         filename=os.path.join(out_dir, svg_name),
         svg_attributes=svg_attrs,
         colors=colors,
        stroke_widths=[0.1]*len(new_paths))
   
main()
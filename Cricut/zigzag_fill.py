import os
import random

import numpy as np
from shapely.geometry import box, LineString, Polygon
from svgpathtools import Line, Path, svg2paths2, wsvg


def remove_duplicate_paths(paths):
    seen = set()
    unique = []
    for p in paths:
        if not isinstance(p, Path):
            continue
        sig = p.d()
        if sig not in seen:
            seen.add(sig)
            unique.append(p)
    return unique


def sample_path_to_polygon(path, num_samples=1000):
    points = [path.point(i / num_samples) for i in range(num_samples)]
    coords = [(pt.real, pt.imag) for pt in points]
    coords.append(coords[0])
    return Polygon(coords)


def shapely_polygon_to_svgpath(poly):
    exterior = list(poly.exterior.coords)
    segments = []
    for i in range(len(exterior) - 1):
        start = complex(*exterior[i])
        end = complex(*exterior[i + 1])
        segments.append(Line(start, end))
    return Path(*segments)


def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def zigzag_fill(path, step=5, overshoot=10, path_buf=0.1, x_tolerance_epsilon=1e-2):
    pts = [(seg.start.real, seg.start.imag) for seg in path]
    if len(pts) < 2:
        return None
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    xmin, xmax, ymin, ymax = path.bbox()
    xs = np.arange(xmin, xmax + step, step)
    poly = sample_path_to_polygon(path, num_samples=10000)
    safe_poly = poly.buffer(path_buf)
    safe_path = shapely_polygon_to_svgpath(safe_poly)
    groups = []

    def intersect_with(line):
        hits = []
        for seg in path:
            if seg.start == seg.end:
                continue
            for t, _ in seg.intersect(line):
                hits.append(seg.point(t))
        hits.sort(key=lambda p: p.imag)
        return list(zip(hits[::2], hits[1::2]))

    for x in xs:
        line = Line(complex(x, ymin - overshoot), complex(x, ymax + overshoot))
        pairs = intersect_with(line)
        for p in pairs:
            matched = False
            for grp in groups:
                last = grp[-1]
                scan = LineString([
                    (last[1].real, last[1].imag),
                    (p[0].real,    p[0].imag)
                ])
                dx = abs(p[0].real - last[1].real)
                
                if abs(dx - step) < x_tolerance_epsilon and safe_poly.covers(scan):
                    grp.append(p)
                    matched = True
                    break
            if not matched:
                groups.append([p])

    result = []
    for grp in groups:
        if not grp:
            continue
        zig = Path(Line(grp[0][0], grp[0][1]))
        last = grp[0]
        for nxt in grp[1:]:
            zig.append(Line(last[1], nxt[0]))
            zig.append(Line(nxt[0], nxt[1]))
            last = nxt
        result.append(zig)
    return result


def get_border_path(svg_attrs): 
    if "viewBox" in svg_attrs:
        vb = list(map(float, svg_attrs["viewBox"].split()))
        _, _, width, height = vb
    else:
        width = float(svg_attrs.get("width", 0).rstrip("px"))
        height = float(svg_attrs.get("height", 0).rstrip("px"))

    border = Path(
        Line(0+0j, width+0j),
        Line(width+0j, width+height*1j),
        Line(width+height*1j, 0+height*1j),
        Line(0+height*1j, 0+0j),
    )
    return border

def sort_paths_by_proximity(paths):
    if not paths:
        return []

    # Extract start and end points for each path
    endpoints = [(p[0].start, p[-1].end) for p in paths]

    # Start with the first path
    sorted_paths = [paths[0]]
    used = {0}

    while len(sorted_paths) < len(paths):
        last_end = sorted_paths[-1][-1].end
        min_dist = float("inf")
        next_idx = None

        # Find the closest path start to the last endpoint
        for i, (start, end) in enumerate(endpoints):
            if i in used:
                continue
            dist = abs(last_end - start)
            if dist < min_dist:
                min_dist = dist
                next_idx = i

        sorted_paths.append(paths[next_idx])
        used.add(next_idx)

    return sorted_paths


def paths_to_zigzag_paths(paths, angle, step, slice_height=5.0):
    new_paths = []

    global global_xmin
    global_xmin = min(p.bbox()[0] for p in paths)
    
    for path in paths:
        xmin, xmax, ymin, ymax = path.bbox()
        center = complex((xmin + xmax)/2, (ymin + ymax)/2)
        
        if slice_height is None or slice_height <= 0 or slice_height >= (ymax - ymin):
            bands = [(ymin, ymax)]  # one single band (no slicing)
        else:
            bands = []
            y = ymin
            while y < ymax:
                bands.append((y, min(y + slice_height, ymax)))
                y += slice_height
       
        for y0, y1 in bands:
            band = box(xmin, y0, xmax, y1)
            base_poly = sample_path_to_polygon(path, num_samples=500)
            try:
                poly0 = base_poly.buffer(0)
                slice_poly = poly0.intersection(band)
            except :
                slice_poly = base_poly.buffer(0).intersection(band)
            if slice_poly.is_empty:
                continue
            slices = ([slice_poly] if isinstance(slice_poly, Polygon)
                      else list(slice_poly.geoms))
            for sp in slices:
                slice_path = shapely_polygon_to_svgpath(sp)
                sxmin, sxmax, symin, symax = slice_path.bbox()
                slice_center = complex((sxmin + sxmax) / 2, (symin + symax) / 2)
                rotated = slice_path.rotated(angle, origin=slice_center)
                zigzags = zigzag_fill(
                    path=rotated,
                    step=step,
                    overshoot=1,
                    path_buf=.2,
                    x_tolerance_epsilon=1
                )
                if zigzags:
                    for z in zigzags:
                        new_paths.append(z.rotated(-angle, origin=slice_center))
                else:
                    new_paths.append(slice_path)
    new_paths = remove_duplicate_paths(new_paths)
    new_paths = sort_paths_by_proximity(new_paths)
    print(f"There are {len(new_paths)} paths")
    return new_paths
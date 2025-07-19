"""
import random
import math
import numpy as np
from shapely.geometry import LineString, Polygon, box, MultiLineString, MultiPolygon
from svgpathtools import Line, Path

DEFAULT_SLICE_HEIGHT = 5.0  
global_xmin = 0

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

def sample_path_to_polygon(path, num_samples=1000):
    pts = [path.point(i / num_samples) for i in range(num_samples)]
    coords = [(pt.real, pt.imag) for pt in pts]
    coords.append(coords[0])
    return Polygon(coords)


def shapely_geom_to_svgpath(geom):
    if isinstance(geom, Polygon):
        coords = list(geom.exterior.coords)
        segs = [
            Line(complex(x0, y0), complex(x1, y1))
            for (x0, y0), (x1, y1) in zip(coords, coords[1:])
        ]
        return Path(*segs)

    if isinstance(geom, (LineString, MultiLineString)):
        lines = geom.geoms if isinstance(geom, MultiLineString) else [geom]
        paths = []
        for line in lines:
            pts = list(line.coords)
            segs = [
                Line(complex(x0, y0), complex(x1, y1))
                for (x0, y0), (x1, y1) in zip(pts, pts[1:])
            ]
            paths.append(Path(*segs))
        return paths[0] if len(paths) == 1 else paths

    if isinstance(geom, MultiPolygon):
        all_paths = []
        for poly in geom.geoms:
            all_paths.append(shapely_geom_to_svgpath(poly))
        return all_paths

    return Path()


def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def zigzag_fill(path, step, overshoot=10.5, path_buf=0.5, x_tol=1e-2):
    
    pts = [(seg.start.real, seg.start.imag) for seg in path]
    if len(pts) < 2:
        return []
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    xmin, xmax, ymin, ymax = path.bbox()
    grid_start = math.floor(global_xmin / step) * step
    xs = grid_start + np.arange(0, 1e6) * step          # long global sequence
    xs = xs[(xs >= xmin) & (xs <= xmax + step)]          # clip to slice

    # raw and buffered polygon
    raw_poly = sample_path_to_polygon(path, num_samples=2000)
    buffer_poly = raw_poly.buffer(path_buf)
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
        pairs = intersect_with(Line(complex(x, ymin - overshoot), complex(x, ymax + overshoot)))
        for entry, exit in pairs:
            matched = False
            for grp in groups:
                last_entry, last_exit = grp[-1]
                connector = LineString([
                    (last_exit.real, last_exit.imag),
                    (entry.real,    entry.imag)
                ])
                vert_segment = LineString([
                    (entry.real, entry.imag),
                    (exit.real,  exit.imag)
                ])
                dx = abs(entry.real - last_exit.real)
                # only require buffer coverage to allow connectors
                if abs(dx - step) < x_tol and buffer_poly.covers(connector) and buffer_poly.covers(vert_segment):
                    grp.append((entry, exit))
                    matched = True
                    break
            if not matched:
                groups.append([(entry, exit)])

    zigzags = []
    for grp in groups:
        if not grp:
            continue
        segs = [(grp[0][0], grp[0][1])]
        last_entry, last_exit = grp[0]
        for entry, exit in grp[1:]:
            segs.append((last_exit, entry))
            segs.append((entry, exit))
            last_entry, last_exit = entry, exit

        # clip using raw_poly
        clipped = []
                # clip using raw_poly and handle all geometry types safely
        clipped = []
        for a, b in segs:
            line = LineString([(a.real, a.imag), (b.real, b.imag)])
            inter = raw_poly.intersection(line)
            if inter.is_empty:
                continue
            # flatten any geometry collection we might get
            if isinstance(inter, LineString):
                geoms = [inter]
            elif isinstance(inter, MultiLineString):
                geoms = list(inter.geoms)
            elif isinstance(inter, (MultiPolygon, Polygon)):
                # intersecting a line with a polygon gives LineStrings along the boundary
                geoms = [g for g in inter.boundary.geoms] if hasattr(inter, "boundary") else []
            else:
                # GeometryCollection: filter LineStrings
                geoms = [g for g in getattr(inter, "geoms", []) if isinstance(g, LineString)]
            for geom in geoms:
                coords = list(geom.coords)
                if len(coords) < 2:
                    continue
                p0, p1 = coords[0], coords[-1]
                clipped.append(Line(complex(*p0), complex(*p1)))

        if clipped:
            zigzags.append(Path(*clipped))

    return zigzags

def paths_to_zigzag_paths(paths, angle, step, slice_height=DEFAULT_SLICE_HEIGHT):
    output = []
    global_xmin = min(p.bbox()[0] for p in paths)
    for path in paths:
        xmin, xmax, ymin, ymax = path.bbox()
            
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
                slice_path = shapely_geom_to_svgpath(sp)
                sxmin, sxmax, symin, symax = slice_path.bbox()
                slice_center = complex((sxmin + sxmax) / 2, (symin + symax) / 2)
                rotated = slice_path.rotated(angle, origin=slice_center)
                zigzags = zigzag_fill(
                    rotated,
                    step,
                    overshoot=0.1,
                    path_buf=0.1,
                    x_tol=0.5
                )
                if zigzags:
                    for z in zigzags:
                        output.append(z.rotated(-angle, origin=slice_center))
                else:
                    output.append(slice_path)
                    
    return remove_duplicate_paths(output)
"""

import os
import random

import numpy as np
from shapely.geometry import LineString, Polygon
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


def zigzag_fill(path, step=5, overshoot=10, path_buf=8, x_tolerance_epsilon=1e-2):
    pts = [(seg.start.real, seg.start.imag) for seg in path]
    if len(pts) < 3:
        return None
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    xmin, xmax, ymin, ymax = path.bbox()
    xs = np.arange(xmin, xmax + step, step)
    poly = sample_path_to_polygon(path, num_samples=500)
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

    if not groups:
        debug = [safe_path]
        for x in xs:
            line = Line(complex(x, ymin - overshoot), complex(x, ymax + overshoot))
            for seg in path:
                if seg.start == seg.end:
                    continue
                for t, _ in seg.intersect(line):
                    pt = seg.point(t)
                    r = 0.25
                    debug.extend([
                        Line(pt - r, pt + r),
                        Line(pt - r * 1j, pt + r * 1j),
                    ])
        return debug

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

    result.append(safe_path)
    return result

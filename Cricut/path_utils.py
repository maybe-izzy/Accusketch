import random
from shapely.ops import unary_union
import math
import numpy as np
from shapely.prepared import prep
from shapely.geometry import box, LineString, Polygon, GeometryCollection
from svgpathtools import Line, Path, wsvg
from shapely.strtree import STRtree
from numbers import Integral

_fix = lambda g: g.buffer(0)


def save_paths(paths, filepath, svg_attrs, with_border=True):
    if with_border:
        paths.extend(get_border_path(svg_attrs=svg_attrs))

    colors = [random_color() for _ in paths]

    wsvg(
        paths,
        filename=filepath,
        svg_attributes=svg_attrs,
        colors=colors,
        stroke_widths=[0.1] * len(paths)
    )


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


def svgpath_to_shapely_polygon(path, step=1.5, min_pts=25, max_pts=10000):
    """
    Robust conversion of an svgpathtools.Path into a Shapely polygon.
    Handles multiple sub-contours, applies even-odd logic via symmetric difference,
    and falls back to containment-based exterior+holes construction.
    """
    # 1. Decompose into contiguous subpaths (split on discontinuity)
    subpaths = []
    current_segs = []
    prev_end = None
    for seg in path:
        if not hasattr(seg, "start") or not hasattr(seg, "end"):
            continue
        if prev_end is not None and abs(seg.start - prev_end) > 1e-6:
            if current_segs:
                subpaths.append(Path(*current_segs))
            current_segs = []
        current_segs.append(seg)
        prev_end = seg.end
    if current_segs:
        subpaths.append(Path(*current_segs))

    def sample(subpath):
        L = max(subpath.length(error=1e-3), 1e-9)
        n = int(np.clip(math.ceil(L / step), min_pts, max_pts))
        ts = np.linspace(0.0, 1.0, n, endpoint=False)
        pts = [subpath.point(t) for t in ts]
        pts.append(subpath.point(1.0))
        coords = [(pt.real, pt.imag) for pt in pts]
        poly = Polygon(coords)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            return None
        return poly

    polys = []
    for sp in subpaths:
        p = sample(sp)
        if p is not None:
            polys.append(p)

    if not polys:
        return Polygon()

    # Even-odd: symmetric difference of all polygons
    filled = polys[0]
    for p in polys[1:]:
        filled = filled.symmetric_difference(p)
    if not filled.is_empty:
        return filled

    # Fallback: build outer+holes via containment
    parents = {i: None for i in range(len(polys))}
    for i, pi in enumerate(polys):
        for j, pj in enumerate(polys):
            if i == j:
                continue
            if pj.contains(pi):
                if parents[i] is None or pj.area < polys[parents[i]].area:
                    parents[i] = j

    outer_idxs = [i for i, parent in parents.items() if parent is None]
    result_polys = []
    for outer in outer_idxs:
        hole_idxs = [i for i, parent in parents.items() if parent == outer]
        holes = []
        for hi in hole_idxs:
            if polys[hi].exterior is not None:
                holes.append(list(polys[hi].exterior.coords))
        newpoly = Polygon(list(polys[outer].exterior.coords), holes=holes)
        if not newpoly.is_valid:
            newpoly = newpoly.buffer(0)
        result_polys.append(newpoly)

    if not result_polys:
        return polys[0]
    if len(result_polys) == 1:
        return result_polys[0]
    return unary_union(result_polys)


def shapely_to_svgpathtools_path(poly):
    """
    Converts a shapely Polygon or MultiPolygon (with holes) into an svgpathtools.Path.
    """
    segments = []

    def ring_to_segments(ring):
        coords = list(ring.coords)
        segs = []
        for a, b in zip(coords, coords[1:]):
            segs.append(Line(complex(*a), complex(*b)))
        return segs

    if poly.geom_type == "Polygon":
        if poly.exterior is not None:
            segments.extend(ring_to_segments(poly.exterior))
        for interior in poly.interiors:
            segments.extend(ring_to_segments(interior))
        return Path(*segments)
    elif poly.geom_type == "MultiPolygon":
        all_segs = []
        for part in poly:
            part_path = shapely_to_svgpathtools_path(part)
            all_segs.extend(list(part_path))
        return Path(*all_segs)
    else:
        return Path()


def build_containment_tree(polys):
    """
    Given list of (original_path, shapely_polygon), returns parent and children maps.
    parents: idx -> parent idx or None
    children: idx -> list of immediate children
    """
    n = len(polys)
    parents = {i: None for i in range(n)}
    for i, (_, pi) in enumerate(polys):
        for j, (_, pj) in enumerate(polys):
            if i == j:
                continue
            if pj.contains(pi):
                if parents[i] is None or pj.area < polys[parents[i]][1].area:
                    parents[i] = j
    children = {i: [] for i in range(n)}
    for i, parent in parents.items():
        if parent is not None:
            children[parent].append(i)
    return parents, children


def assemble_holey_polygons(polys):
    """
    Collapse outer+hole hierarchies into final shapely geometries, handling nested
    holes/islands via recursive symmetric differences.
    Input: list of tuples (original_path, shapely_polygon)
    Output: list of merged shapely geometries (one per top-level outer)
    """
    parents, children = build_containment_tree(polys)
    outer_idxs = [i for i, p in parents.items() if p is None]
    result = []

    def build_recursive(idx):
        base = polys[idx][1]
        child_geoms = []
        for child in children.get(idx, []):
            child_geom = build_recursive(child)
            child_geoms.append(child_geom)
        if not child_geoms:
            return base
        combined = base
        for cg in child_geoms:
            combined = combined.symmetric_difference(cg)
        return combined

    for outer in outer_idxs:
        merged = build_recursive(outer)
        if not merged.is_valid:
            merged = merged.buffer(0)
        result.append(merged)
    return result


def merge_outer_and_hole_paths(paths, *, sampling_step=1.5, min_pts=25, max_pts=10000):
    """
    Given a list of svgpathtools.Path objects that share the same fill (outer + hole
    as separate <path> elements), collapse them into merged hole-aware Paths.
    """
    # Build (original, shapely) list
    polys = []
    for p in paths:
        poly = svgpath_to_shapely_polygon(p, step=sampling_step,
                                          min_pts=min_pts, max_pts=max_pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        polys.append((p, poly))

    if not polys:
        return []

    # Assemble with hierarchy
    merged_shapely = assemble_holey_polygons(polys)
    if not merged_shapely:
        # fallback: return originals
        return paths

    merged_paths = []
    for shp in merged_shapely:
        svg_path = shapely_to_svgpathtools_path(shp)
        merged_paths.append(svg_path)
    return merged_paths


def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def parse_style(style_str: str) -> dict:
    d = {}
    for part in style_str.strip().split(';'):
        if ':' in part:
            k, v = part.split(':', 1)
            d[k.strip()] = v.strip()
    return d


def filter_paths_by_color(paths, attrs, color):
    filtered_paths = []
    for path, attr in zip(paths, attrs):
        path_color = parse_style(attr.get("style", "")).get("fill")
        if path_color == color:
            filtered_paths.append(path)
    return filtered_paths


def _clean(g):
    g = _fix(g)
    if g.is_empty:
        return None
    if isinstance(g, GeometryCollection) and len(g.geoms) == 1:
        g = g.geoms[0]
    return g


def filter_nested_paths(
        paths,
        *,
        num_samples: int = 800,
        tol: float = 1e-3
    ):
    """
    Remove any path that lies completely inside (or on the edge of)
    another path, regardless of SVG stacking order.
    """
    polys = []
    keep_flags = [True] * len(paths)

    # 1) build polygons once
    for p in paths:
        polys.append(_clean(svgpath_to_shapely_polygon(p)))

    # 2) make a list of *valid* polygons for the STRtree
    valid_polys = [poly for poly in polys if poly is not None]
    poly_to_index = {id(poly): i for i, poly in enumerate(polys) if poly is not None}

    tree = STRtree(valid_polys)

    # 3) test each polygon against potential supersets
    for i, poly in enumerate(polys):
        if poly is None:
            continue  # keep strokes / invalid → can’t be “inside” a fill

        candidates = tree.query(poly)

        for candidate in candidates:
            if isinstance(candidate, Integral):
                sup_poly = valid_polys[int(candidate)]
            else:
                sup_poly = candidate

            if sup_poly is poly or sup_poly.equals(poly):
                continue

            if sup_poly.buffer(tol).covers(poly):
                keep_flags[i] = False
                break

    return [p for p, keep in zip(paths, keep_flags) if keep]


def zigzag_fill(path, step=5, overshoot=10, path_buf=0.1, x_tolerance_epsilon=1e-2):
    pts = [(seg.start.real, seg.start.imag) for seg in path]
    if len(pts) < 2:
        return None
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    xmin, xmax, ymin, ymax = path.bbox()
    xs = np.arange(xmin, xmax + step, step)
    poly = svgpath_to_shapely_polygon(path, step)
    safe_poly = poly.buffer(path_buf)
    prepared_safe = prep(safe_poly)
    groups = []

    # Precompute vertical extents for each segment to short-circuit intersection tests
    segment_bounds = []
    for seg in path:
        if hasattr(seg, "start") and hasattr(seg, "end"):
            y_coords = [seg.start.imag, seg.end.imag]
            ymin_seg, ymax_seg = min(y_coords), max(y_coords)
            segment_bounds.append((seg, ymin_seg, ymax_seg))
        else:
            segment_bounds.append((seg, -1e9, 1e9))  # fallback

    def intersect_with(line):
        hits = []
        x_coord = line.start.real  # vertical line at this x
        for seg, ymin_seg, ymax_seg in segment_bounds:
            # quick reject: if vertical line's y-range is disjoint from segment's bbox y-range, skip
            # (assuming line spans full y anyway; you could optimize further if needed)
            if seg.start == seg.end:
                continue
            # optional: skip if x is far from seg's bbox in x; compute seg bbox once if needed
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

                if abs(dx - step) < x_tolerance_epsilon and prepared_safe.covers(scan):
                    grp.append(p)
                    matched = True
                    break
            if not matched:
                groups.append([p])

    result = []
    result_mid = []

    for grp in groups:
        if not grp:
            continue
        longest_line_len = 0
        num_lines = 1
        zig = Path(Line(grp[0][0], grp[0][1]))
        last = grp[0]
        for nxt in grp[1:]:
            first_line = Line(last[1], nxt[0])
            second_line = Line(nxt[0], nxt[1])

            if first_line.length() > longest_line_len:
                longest_line_len = first_line.length()
            elif second_line.length() > longest_line_len:
                longest_line_len = second_line.length()

            zig.append(Line(last[1], nxt[0]))
            zig.append(Line(nxt[0], nxt[1]))
            num_lines += 2
            last = nxt

        if longest_line_len >= 3.5 and num_lines >= 5:
            #print(f"longest_line_len: {longest_line_len}, num_lines: {num_lines}")
            result.append(zig)
        else:
            result_mid.append(zig)
    return result, result_mid


def get_border_path(svg_attrs):
    if "viewBox" in svg_attrs:
        vb = list(map(float, svg_attrs["viewBox"].split()))
        _, _, width, height = vb
    else:
        width = float(svg_attrs.get("width", 0).rstrip("px"))
        height = float(svg_attrs.get("height", 0).rstrip("px"))

    border = Path(
        Line(0 + 0j, width + 0j),
        Line(width + 0j, width + height * 1j),
        Line(width + height * 1j, 0 + height * 1j),
        Line(0 + height * 1j, 0 + 0j),
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
    new_paths_small = []

    global global_xmin
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
       
        base_poly = svgpath_to_shapely_polygon(path, step)
        for y0, y1 in bands:
            band = box(xmin, y0, xmax, y1)
           
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
                slice_path = shapely_to_svgpathtools_path(sp)
                sxmin, sxmax, symin, symax = slice_path.bbox()
                slice_center = complex((sxmin + sxmax) / 2, (symin + symax) / 2)
                rotated = slice_path.rotated(angle, origin=slice_center)
                zigzags_reg, zigzag_small = zigzag_fill(
                    path=rotated,
                    step=step,
                    overshoot=1,
                    path_buf=.2,
                    x_tolerance_epsilon=1
                )
                
                if zigzags_reg:
               
                    for z in zigzags_reg:
                        new_paths.append(z.rotated(-angle, origin=slice_center))
                elif zigzag_small:
           
                    for z in zigzag_small:
                        new_paths_small.append(z.rotated(-angle, origin=slice_center))
                if not zigzags_reg and not zigzag_small:
                    new_paths_small.append(slice_path)

    new_paths = remove_duplicate_paths(new_paths)
    new_paths_small = remove_duplicate_paths(new_paths_small)

    return new_paths, new_paths_small
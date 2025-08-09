import random
from shapely.ops import unary_union, split, nearest_points
import math
import numpy as np
from shapely.prepared import prep
from shapely.geometry import (
    box,
    LineString,
    Polygon,
    GeometryCollection,
    MultiPolygon,
    Point,
    MultiPoint,
)
from svgpathtools import Line, Path, wsvg
from shapely.strtree import STRtree
from numbers import Integral

_fix = lambda g: g.buffer(0)


# ==========================
# I/O, colors, misc helpers
# ==========================

def save_paths(paths, filepath, svg_attrs, with_border=True, with_color=True):
    if with_border:
        paths = get_border_path(svg_attrs=svg_attrs) + paths

    colors = None
    if with_color:
        colors = [random_color() for _ in paths]

    wsvg(
        paths,
        filename=filepath,
        svg_attributes=svg_attrs,
        stroke_widths=[0.1] * len(paths),
        colors=colors,
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


# ==========================
# SVG <-> Shapely conversion
# ==========================

def svgpath_to_shapely_polygon(path, step=1.5, min_pts=25, max_pts=10000):
    """
    Robust conversion of an svgpathtools.Path into a Shapely polygon.
    Handles multiple sub-contours, applies even-odd via symmetric difference,
    then containment fallback.
    """
    # Split on discontinuities
    subpaths = []
    current = []
    prev_end = None
    for seg in path:
        if not hasattr(seg, "start") or not hasattr(seg, "end"):
            continue
        if prev_end is not None and abs(seg.start - prev_end) > 1e-6:
            if current:
                subpaths.append(Path(*current))
            current = []
        current.append(seg)
        prev_end = seg.end
    if current:
        subpaths.append(Path(*current))

    def sample(sp):
        L = max(sp.length(error=1e-3), 1e-9)
        n = int(np.clip(math.ceil(L / step), min_pts, max_pts))
        ts = np.linspace(0.0, 1.0, n, endpoint=False)
        pts = [sp.point(t) for t in ts]
        pts.append(sp.point(1.0))
        coords = [(pt.real, pt.imag) for pt in pts]
        poly = Polygon(coords)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return None if poly.is_empty else poly

    polys = []
    for sp in subpaths:
        p = sample(sp)
        if p is not None:
            polys.append(p)
    if not polys:
        return Polygon()

    filled = polys[0]
    for p in polys[1:]:
        filled = filled.symmetric_difference(p)
    if not filled.is_empty:
        return filled

    # containment fallback
    parents = {i: None for i in range(len(polys))}
    for i, pi in enumerate(polys):
        for j, pj in enumerate(polys):
            if i == j:
                continue
            if pj.contains(pi):
                if parents[i] is None or pj.area < polys[parents[i]].area:
                    parents[i] = j

    outers = [i for i, pr in parents.items() if pr is None]
    result_polys = []
    for oi in outers:
        hole_idxs = [i for i, pr in parents.items() if pr == oi]
        holes = [list(polys[hi].exterior.coords) for hi in hole_idxs if polys[hi].exterior is not None]
        newpoly = Polygon(list(polys[oi].exterior.coords), holes=holes)
        if not newpoly.is_valid:
            newpoly = newpoly.buffer(0)
        result_polys.append(newpoly)

    if not result_polys:
        return polys[0]
    if len(result_polys) == 1:
        return result_polys[0]
    return unary_union(result_polys)


def shapely_to_svgpathtools_path(poly):
    """Convert Polygon/MultiPolygon/GeometryCollection to Path (exterior+holes)."""
    segments = []

    def ring_to_segments(ring):
        coords = list(ring.coords)
        segs = []
        for a, b in zip(coords, coords[1:]):
            segs.append(Line(complex(*a), complex(*b)))
        return segs

    if isinstance(poly, Polygon):
        if poly.exterior is not None:
            segments.extend(ring_to_segments(poly.exterior))
        for interior in poly.interiors:
            segments.extend(ring_to_segments(interior))
        return Path(*segments)

    if isinstance(poly, MultiPolygon) or hasattr(poly, "geoms"):
        for part in getattr(poly, "geoms", []):
            part_path = shapely_to_svgpathtools_path(part)
            segments.extend(list(part_path))
        return Path(*segments)

    return Path()


# ===============================
# Containment + hole assembly API
# ===============================

def build_containment_tree(polys):
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
    for i, pr in parents.items():
        if pr is not None:
            children[pr].append(i)
    return parents, children


def assemble_holey_polygons(polys):
    parents, children = build_containment_tree(polys)
    outers = [i for i, pr in parents.items() if pr is None]
    result = []

    def build_recursive(idx):
        base = polys[idx][1]
        kids = [build_recursive(k) for k in children.get(idx, [])]
        if not kids:
            return base
        combined = base
        for cg in kids:
            combined = combined.symmetric_difference(cg)
        return combined

    for oi in outers:
        merged = build_recursive(oi)
        if not merged.is_valid:
            merged = merged.buffer(0)
        result.append(merged)
    return result


def merge_outer_and_hole_paths(paths, *, sampling_step=1.5, min_pts=25, max_pts=10000):
    polys = []
    for p in paths:
        poly = svgpath_to_shapely_polygon(p, step=sampling_step, min_pts=min_pts, max_pts=max_pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        polys.append((p, poly))

    if not polys:
        return []

    merged_shapely = assemble_holey_polygons(polys)
    if not merged_shapely:
        return paths

    merged_paths = [shapely_to_svgpathtools_path(shp) for shp in merged_shapely]
    return merged_paths


# ======================
# Filtering / utilities
# ======================

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


def filter_nested_paths(paths, *, num_samples: int = 800, tol: float = 1e-3):
    polys = []
    keep_flags = [True] * len(paths)

    for p in paths:
        polys.append(_clean(svgpath_to_shapely_polygon(p)))

    valid_polys = [poly for poly in polys if poly is not None]
    poly_to_index = {id(poly): i for i, poly in enumerate(polys) if poly is not None}

    tree = STRtree(valid_polys)

    for i, poly in enumerate(polys):
        if poly is None:
            continue
        candidates = tree.query(poly)
        for candidate in candidates:
            sup_poly = valid_polys[int(candidate)] if isinstance(candidate, Integral) else candidate
            if sup_poly is poly or sup_poly.equals(poly):
                continue
            if sup_poly.buffer(tol).covers(poly):
                keep_flags[i] = False
                break

    return [p for p, keep in zip(paths, keep_flags) if keep]


# ======================
# Zigzag generation core
# ======================

def zigzag_fill(path, step=5, overshoot=10, path_buf=0.1, x_tolerance_epsilon=1e-2):
    """
    Build *segments* of zigzags inside a (rotated) path using vertical scans.
    Returns (segments_long, segments_short) as lists of Path objects (Lines only).
    """
    pts = [(seg.start.real, seg.start.imag) for seg in path]
    if len(pts) < 2:
        return [], []
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    xmin, xmax, ymin, ymax = path.bbox()
    xs = np.arange(xmin, xmax + step, step)
    poly = svgpath_to_shapely_polygon(path, step)
    safe_poly = poly.buffer(path_buf)
    prepared_safe = prep(safe_poly)
    groups = []

    segment_bounds = []
    for seg in path:
        if hasattr(seg, "start") and hasattr(seg, "end"):
            y_coords = [seg.start.imag, seg.end.imag]
            ymin_seg, ymax_seg = min(y_coords), max(y_coords)
            segment_bounds.append((seg, ymin_seg, ymax_seg))
        else:
            segment_bounds.append((seg, -1e9, 1e9))

    def intersect_with(line):
        hits = []
        for seg, ymin_seg, ymax_seg in segment_bounds:
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
                scan = LineString([(last[1].real, last[1].imag), (p[0].real, p[0].imag)])
                dx = abs(p[0].real - last[1].real)
                if abs(dx - step) < x_tolerance_epsilon and prepared_safe.covers(scan):
                    grp.append(p)
                    matched = True
                    break
            if not matched:
                groups.append([p])

    segments_long, segments_short = [], []
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
            segments_long.append(zig)
        else:
            segments_short.append(zig)
    return segments_long, segments_short


# =========================================
# NEW: safe in-polygon connectors + stitching
# =========================================

def _c(z: complex) -> tuple:
    return (z.real, z.imag)


def _reverse_path(p: Path) -> Path:
    # Zig segments are Lines only.
    segs = list(p)
    rev = [Line(s.end, s.start) for s in reversed(segs)]
    return Path(*rev)


def _append_linestring(path: Path, ls: LineString):
    coords = list(ls.coords)
    if not coords:
        return
    # Avoid a duplicate zero-length line if the first coord equals path end
    for i in range(len(coords) - 1):
        a = complex(*coords[i])
        b = complex(*coords[i + 1])
        if a != b:
            path.append(Line(a, b))


def _direct_inside(safe_poly, a: complex, b: complex) -> bool:
    return safe_poly.covers(LineString([_c(a), _c(b)]))


def _boundary_detour(poly: Polygon, a: complex, b: complex) -> LineString:
    """
    Build the shortest boundary route between a and b by:
      1) projecting a,b to each ring (exterior + holes),
      2) splitting the ring at those points,
      3) choosing the shorter of the two resulting ring paths,
      4) prefixing/suffixing tiny straight stubs from a->pa and pb->b (checked later).
    Returns a LineString of boundary-only portion (pa..pb) — caller will add stubs.
    """
    rings = [poly.exterior] + list(poly.interiors)
    best = None
    best_len = float("inf")

    for ring in rings:
        if ring is None:
            continue
        line = LineString(list(ring.coords))  # closed (first==last)
        pa = nearest_points(Point(_c(a)), line)[1]  # point on line
        pb = nearest_points(Point(_c(b)), line)[1]
        try:
            parts = split(line, MultiPoint([pa, pb]))
        except Exception:
            # Fallback: if split fails due to numeric quirks, just use the whole ring
            parts = [line]
        candidates = []
        if hasattr(parts, "geoms"):
            candidates = list(parts.geoms)
        else:
            candidates = [parts]
        # Expect 2 parts on a closed ring; handle oddities gracefully
        for seg in candidates:
            # Orient seg so it goes pa -> pb
            coords = list(seg.coords)
            if coords:
                # If reversed matches better, reverse
                if Point(coords[0]).distance(pa) > Point(coords[-1]).distance(pa):
                    coords = list(reversed(coords))
            seg_ls = LineString(coords)
            # ensure both endpoints are near pa/pb
            if pa.distance(Point(seg_ls.coords[0])) < 1e-6 and pb.distance(Point(seg_ls.coords[-1])) < 1e-6 or \
               pb.distance(Point(seg_ls.coords[0])) < 1e-6 and pa.distance(Point(seg_ls.coords[-1])) < 1e-6:
                L = seg_ls.length
                if L < best_len:
                    best_len = L
                    # normalize orientation pa->pb
                    if pb.distance(Point(seg_ls.coords[0])) < pa.distance(Point(seg_ls.coords[0])):
                        seg_ls = LineString(list(reversed(list(seg_ls.coords))))
                    best = seg_ls
        # If we didn't get two proper parts (rare), just keep shortest segment
        if best is None and candidates:
            c0 = min(candidates, key=lambda s: s.length)
            best = c0
            best_len = c0.length

    return best if best is not None else LineString([])


def _route_inside(poly: Polygon, a: complex, b: complex, path_buf: float = 0.4) -> LineString:
    safe_poly = poly.buffer(path_buf)
    if _direct_inside(safe_poly, a, b):
        return LineString([_c(a), _c(b)])

    # Boundary detour: a -> pa .. pb -> b
    core = _boundary_detour(poly, a, b)
    if core.is_empty:
        # give up: return direct clipped to interior (very rare)
        return LineString([_c(a), _c(b)])

    # Build full route with short stubs to/from boundary
    pa = core.coords[0]
    pb = core.coords[-1]
    route_coords = [_c(a), pa] + list(core.coords)[1:-1] + [pb, _c(b)]
    # Clean consecutive duplicates
    cleaned = [route_coords[0]]
    for pt in route_coords[1:]:
        if pt != cleaned[-1]:
            cleaned.append(pt)
    return LineString(cleaned)


def _path_end(p: Path) -> complex:
    return p[-1].end if len(p) else None


def _path_start(p: Path) -> complex:
    return p[0].start if len(p) else None


def stitch_segments_into_one_path(poly: Polygon, segments: list, *, path_buf: float = 0.4) -> Path | None:
    """
    Greedy stitching: pick a start, then repeatedly connect to the nearest *reachable*
    next segment (optionally reversed) using a connector routed *inside* the polygon.
    Produces a SINGLE Path with one initial Move.
    """
    segs = [s for s in segments if len(s) > 0]
    if not segs:
        return None

    # Start: choose the segment with the smallest (x,y) start
    def key_start(p):
        s = _path_start(p)
        return (s.real, s.imag)

    used = [False] * len(segs)
    start_idx = min(range(len(segs)), key=lambda i: key_start(segs[i]))
    current = segs[start_idx]
    used[start_idx] = True

    stitched = Path(*list(current))  # copy
    current_end = _path_end(stitched)

    # Greedy connect remaining
    while not all(used):
        best = None
        best_idx = None
        best_rev = False
        best_len = float("inf")

        for i, seg in enumerate(segs):
            if used[i]:
                continue
            s0, e0 = _path_start(seg), _path_end(seg)
            # try normal
            route = _route_inside(poly, current_end, s0, path_buf)
            L = route.length if not route.is_empty else float("inf")
            if L < best_len:
                best = route
                best_idx = i
                best_rev = False
                best_len = L
            # try reversed (sometimes much shorter)
            rseg = _reverse_path(seg)
            s1 = _path_start(rseg)
            route_r = _route_inside(poly, current_end, s1, path_buf)
            Lr = route_r.length if not route_r.is_empty else float("inf")
            if Lr < best_len:
                best = route_r
                best_idx = i
                best_rev = True
                best_len = Lr

        # Append connector then the chosen segment
        if best is not None and not best.is_empty:
            _append_linestring(stitched, best)
        chosen = _reverse_path(segs[best_idx]) if best_rev else segs[best_idx]
        for seg in chosen:
            stitched.append(seg)
        used[best_idx] = True
        current_end = _path_end(stitched)

    return stitched


# ===============================
# Border adorners (unchanged API)
# ===============================

def _parse_len(v):
    s = str(v).strip()
    for suf in ("in", "pt", "px", "cm", "mm"):
        if s.endswith(suf):
            num = float(s[:-len(suf)])
            return num, suf
    return float(s), ""


def _units_per_inch(svg_attrs):
    vb = svg_attrs.get("viewBox")
    w_raw = svg_attrs.get("width")
    if w_raw is not None and vb:
        w_val, w_unit = _parse_len(w_raw)
        if w_unit == "in":
            vb_w = float(vb.split()[2])
            return vb_w / w_val
        if w_unit == "pt":
            return 72.0
        if w_unit == "px":
            return 96.0
    return 72.0


def _canvas_size(svg_attrs):
    if "viewBox" in svg_attrs:
        _, _, w, h = map(float, svg_attrs["viewBox"].split())
        return w, h
    def _num(v):
        val, _ = _parse_len(v)
        return val
    return _num(svg_attrs.get("width", 0)), _num(svg_attrs.get("height", 0))


def _rect_path(x0, y0, x1, y1):
    return Path(
        Line(complex(x0, y0), complex(x1, y0)),
        Line(complex(x1, y0), complex(x1, y1)),
        Line(complex(x1, y1), complex(x0, y1)),
        Line(complex(x0, y1), complex(x0, y0)),
    )


def _cross_at(x, y, half):
    return Path(
        Line(complex(x - half, y), complex(x + half, y)),
        Line(complex(x, y - half), complex(x, y + half)),
    )


def get_border_path(
    svg_attrs,
    *,
    add_corner_rects=True,
    rect_count=4,
    rect_width_in=0.5,
    rect_height_in=0.5,
    margin_in=0.0,
    spacing_in=0.5,
    orientation="horizontal",
):
    W, H = _canvas_size(svg_attrs)
    upi = _units_per_inch(svg_attrs)
    half = (0.01 * upi) / 2.0
    m = margin_in * upi
    pts = [(m, m), (W - m, m), (W - m, H - m), (m, H - m)]
    out = [_cross_at(x, y, half) for x, y in pts]

    if not add_corner_rects or rect_count <= 0:
        return out

    rw = rect_width_in * upi
    rh = rect_height_in * upi
    m = margin_in * upi
    s = spacing_in * upi

    if orientation.lower().startswith("h"):
        for i in range(rect_count):
            x0 = m + i * (rw + s)
            x1 = x0 + rw
            y1 = H - m
            y0 = y1 - rh
            out.append(_rect_path(x0, y0, x1, y1))
    else:
        for i in range(rect_count):
            x1 = W - m
            x0 = x1 - rw
            y1 = H - m - i * (rh + s)
            y0 = y1 - rh
            out.append(_rect_path(x0, y0, x1, y1))

    return out


# =====================================
# NEW orchestration: one zigzag per path
# =====================================

def sort_paths_by_proximity(paths):
    if not paths:
        return []
    endpoints = [(p[0].start, p[-1].end) for p in paths]
    sorted_paths = [paths[0]]
    used = {0}
    while len(sorted_paths) < len(paths):
        last_end = sorted_paths[-1][-1].end
        min_dist = float("inf")
        next_idx = None
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
    """
    For each input path:
      - make scan slices (if requested),
      - generate zigzag segments (rotated for scan),
      - de-rotate back and **stitch them** into ONE continuous path with safe connectors.

    Returns (stitched_paths, leftovers) to preserve caller signature, but `stitched_paths`
    contains **at most one** Path per input path.
    """
    stitched_paths = []
    leftovers = []  # kept for compatibility / debugging

    for path in paths:
        xmin, xmax, ymin, ymax = path.bbox()
        # Slices: 1 band means whole path
        if slice_height is None or slice_height <= 0 or slice_height >= (ymax - ymin):
            bands = [(ymin, ymax)]
        else:
            bands = []
            y = ymin
            while y < ymax:
                bands.append((y, min(y + slice_height, ymax)))
                y += slice_height

        # Collect all segments across slices
        base_poly = svgpath_to_shapely_polygon(path, step)
        all_segments = []

        for y0, y1 in bands:
            band = box(xmin, y0, xmax, y1)
            try:
                poly0 = base_poly.buffer(0)
                slice_poly = poly0.intersection(band)
            except Exception:
                slice_poly = base_poly.buffer(0).intersection(band)
            if slice_poly.is_empty:
                continue
            pieces = [slice_poly] if isinstance(slice_poly, Polygon) else list(slice_poly.geoms)
            for sp in pieces:
                slice_path = shapely_to_svgpathtools_path(sp)
                sxmin, sxmax, symin, symax = slice_path.bbox()
                slice_center = complex((sxmin + sxmax) / 2, (symin + symax) / 2)
                rotated = slice_path.rotated(angle, origin=slice_center)
                seg_long, seg_short = zigzag_fill(
                    path=rotated, step=step, overshoot=10, path_buf=0.4, x_tolerance_epsilon=1
                )
                # de-rotate back and collect
                for z in seg_long + seg_short:
                    all_segments.append(z.rotated(-angle, origin=slice_center))

        # Stitch into a single continuous zigzag for this input path
        single = stitch_segments_into_one_path(base_poly, all_segments, path_buf=0.4)
        if single is not None and len(single) > 0:
            stitched_paths.append(single)
        else:
            # Fallback: keep nothing (or add outline slice if you prefer)
            pass

    stitched_paths = remove_duplicate_paths(stitched_paths)
    return stitched_paths, leftovers

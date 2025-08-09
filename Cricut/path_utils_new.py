# path_utils.py

import math
from shapely.geometry import LineString, Polygon, MultiPolygon, box, Point
from shapely.ops import unary_union
from shapely.affinity import rotate as shapely_rotate
from svgpathtools import Line, Path

# — your existing helpers (parse_style, get_border_path, random_color, remove_duplicate_paths, assemble_holey_polygons, etc.) remain unchanged —

def sample_path_to_polygon(svg_path, num_samples=500):
    pts = [svg_path.point(i/num_samples) for i in range(num_samples+1)]
    coords = [(p.real, p.imag) for p in pts]
    return Polygon(coords)

def pure_shapely_zigzag(polygons, angle_deg, spacing, slice_height=None):

    if isinstance(polygons, (Polygon, MultiPolygon)):
        poly_list = [polygons]
    else:
        poly_list = list(polygons)

    out_lines = []

    for poly in poly_list:
        # optionally slice into bands
        minx, miny, maxx, maxy = poly.bounds
        bands = [ (miny, maxy) ]
        if slice_height and 0 < slice_height < (maxy-miny):
            bands = []
            y = miny
            while y < maxy:
                bands.append((y, min(y+slice_height, maxy)))
                y += slice_height

        for y0, y1 in bands:
            band = box(minx, y0, maxx, y1)
            chunk = poly.intersection(band)
            if chunk.is_empty:
                continue
            pieces = [chunk] if isinstance(chunk, Polygon) else list(chunk.geoms)

            for piece in pieces:
                # rotate piece → horizontal‐based grid
                #rotated = shapely_rotate(piece, angle_deg, origin='centroid', use_radians=False)
                rminx, rminy, rmaxx, rmaxy = piece.bounds

                # generate zig lines
                n_strips = math.ceil((rmaxy - rminy)/spacing)
                for i in range(n_strips+1):
                    y = rminy + i*spacing
                    base = LineString([(rminx, y), (rmaxx, y)])
                    segs = poly.intersection(base)
                    if segs.is_empty:
                        continue
                    # for MultiLineString vs LineString
                    if (isinstance(segs, Point)):
                        continue
                    segment_list = [segs] if isinstance(segs, LineString) else list(segs.geoms)
                    # preserve zig order by flipping every other row
                    if i % 2 == 1:
                        segment_list = [LineString(list(s.coords)[::-1]) for s in segment_list]
                    # rotate back and collect
                    for seg in segment_list:
                        out_lines.append(
                            seg
                        )

    return out_lines

def shapely_lines_to_svg_paths(lines):
    """
    Convert a list of Shapely LineString → svgpathtools.Path
    """
    paths = []
    for ls in lines:
        coords = list(ls.coords)
        if len(coords) < 2:
            continue
        segments = []
        for a, b in zip(coords, coords[1:]):
            segments.append(Line(complex(*a), complex(*b)))
        paths.append(Path(*segments))
    return paths

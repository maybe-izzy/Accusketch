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
        debug = []
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

    return result



def main():
    svg_name   = "b1.25_united.svg"
    in_dir     = "../svg/input/"
    out_dir    = "../svg/output/"
    paths, attrs, svg_attrs = svg2paths2(os.path.join(in_dir, svg_name))

    new_paths = []
    angle     = 45.0

    for path in paths:
        xmin, xmax, ymin, ymax = path.bbox()
        center = complex((xmin + xmax)/2, (ymin + ymax)/2)

        rotated_shape = path.rotated(angle, origin=center)

        zigzags = zigzag_fill(
            path=rotated_shape,
            step=0.5,
            overshoot=10,
            path_buf=0.25,
            x_tolerance_epsilon=0.5
        )

        if zigzags:
            for zig in zigzags:
                back = zig.rotated(-angle, origin=center)
                new_paths.append(back)
        else:
            new_paths.append(path)

    new_paths = remove_duplicate_paths(new_paths)
    colors = [random_color() for _ in new_paths]
    wsvg(new_paths,
         filename=os.path.join(out_dir, svg_name),
         svg_attributes=svg_attrs,
         colors=colors,
         stroke_widths=[0.1]*len(new_paths))


if __name__ == "__main__":
    main()

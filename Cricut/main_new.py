# main.py

import os
from svgpathtools import svg2paths2, wsvg
from config import Config
from path_utils import (
   
    parse_style,
    assemble_holey_polygons,
     
    remove_duplicate_paths,
    get_border_path,
    random_color,
)
from path_utils_new import (
    sample_path_to_polygon,
    pure_shapely_zigzag,
    shapely_lines_to_svg_paths,

)
def main():
    cfg = Config("config_quickmode.json")
    cfg.print_config()

    # 1) Load every SVG Path + its attributes
    all_paths, all_attrs, svg_attrs = svg2paths2(os.path.join(cfg.get_input_path()))

    # 2) Convert once → Shapely Polygon (via sampling)
    poly_attr = [
        (sample_path_to_polygon(p, num_samples=1000), attr)
        for p, attr in zip(all_paths, all_attrs)
    ]

    zig_lines = []

    # 3) For each "value" bucket: filter, merge, slice, zigzag (all in Shapely)
    for value in cfg.get_values_to_process():
        target_color = cfg.get_color(value)
        filtered = [
            poly for poly, attr in poly_attr
            if parse_style(attr.get("style", "")).get("fill") == target_color
        ]
        if not filtered:
            continue

        # merge into hole-aware polygons
        merged_polys = assemble_holey_polygons([(None, p) for p in filtered])

        angles  = cfg.get_angles(value)
        spacing = cfg.get_spacing(value)
        slices  = cfg.get_slice_sizes(value)

        for angle, step, slice_h in zip(angles, spacing, slices):
            for poly in merged_polys:
                lines = pure_shapely_zigzag(
                    poly,
                    angle_deg=angle,
                    spacing=step,
                    slice_height=slice_h
                )
                zig_lines.extend(lines)

    # 4) Dedupe & convert to svgpathtools.Path
    zig_paths = shapely_lines_to_svg_paths(zig_lines)
    unique_zigs = remove_duplicate_paths(zig_paths)

    # 5) (Optional) add artboard border
    border = get_border_path(svg_attrs)
    unique_zigs.append(border)

    # 6) Write out
    colors = [random_color() for _ in unique_zigs] if cfg.get_save_with_color() else None
    wsvg(
        unique_zigs,
        filename=cfg.get_output_path(extension="_all"),
        svg_attributes=svg_attrs,
        stroke_widths=[0.1]*len(unique_zigs),
        colors=colors,
    )

if __name__ == "__main__":
    main()
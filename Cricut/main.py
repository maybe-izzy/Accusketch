import os
from svgpathtools import svg2paths2
from path_utils import (
    paths_to_zigzag_paths,
    filter_paths_by_color,
    save_paths,
    merge_outer_and_hole_paths,
    svgpath_to_shapely_polygon,
    remove_duplicate_paths
)
from config import Config


def main():
    cfg_filename = "config.json"
    config = Config(cfg_filename)
    config.print_config()

    all_paths, attrs, svg_attrs = svg2paths2(os.path.join(config.get_input_path()))
    
    zigzags = []

    for value in config.get_values_to_process():
        if not config.get_save_single_output():
            zigzags = []

        angles = config.get_angles(value)
        spacing = config.get_spacing(value)
        slice_flags = config.get_slice_sizes(value)
        paths = filter_paths_by_color(all_paths, attrs, config.get_color(value))
        print(f"There are {len(paths)} paths for value: {value}")          

        paths = merge_outer_and_hole_paths(paths)

        save_paths(
            paths,
            config.get_output_path(extension="_outlines"),
            svg_attrs,
            with_border=True,
            with_color=config.get_save_with_color()
        )

        max_area = config.get_max_area()
        min_area = config.get_min_area() 

        paths_to_use = []
        paths_to_outline = []
        
        for path in paths: 
            poly = svgpath_to_shapely_polygon(path)
            
            if max_area != -1 and poly.area >= max_area:
                print("skipping polygon - above configured max polygon area.")

                if config.get_outline_large_polygons(): 
                    print("outlining large polygon")
                    paths_to_outline.append(path)
            elif min_area != -1 and poly.area <= min_area: 
                print("skipping polygon - below configured min polygon area.")

                if config.get_outline_small_polygons(): 
                    print("outlining small polygon")        
                    paths_to_outline.append(path)
            else: 
                paths_to_use.append(path)
        
        if (not paths): 
            continue
        for angle, step, slice_height in zip(angles, spacing, slice_flags):
            zigzags_reg = paths_to_zigzag_paths(
                paths_to_use, angle, step, slice_height=slice_height, with_outline=config.get_with_outline()
            )
            print(f"zigzags: {len(zigzags_reg)}")
            zigzags.extend(zigzags_reg)

            
        if not config.get_save_single_output():
            save_paths(
                remove_duplicate_paths(zigzags) + paths_to_outline,
                config.get_output_path(extension=f"_all_{value}"),
                svg_attrs,
                with_border=True,
                with_color=config.get_save_with_color()
            )

    if config.get_save_single_output():
        all_combined = remove_duplicate_paths(zigzags)
        
        save_paths(
            all_combined + paths_to_outline,
            config.get_output_path(extension="_all"),
            svg_attrs,
            with_border=True,
            with_color=config.get_save_with_color()
        )

if __name__ == "__main__":
    main()

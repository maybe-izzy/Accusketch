import os
import sys
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
    cfg_filename = sys.argv[1]
    config = Config(cfg_filename)
    config.print_config()

    all_paths, attrs, svg_attrs = svg2paths2(os.path.join(config.get_input_path()))
    
    zigzags_for_value = []

    for value in config.get_values_to_process():
        if not config.get_save_single_output():
            zigzags_for_value = []

        angles = config.get_angles(value)
        spacing = config.get_spacing(value)
        slice_flags = config.get_slice_sizes(value)
        paths = filter_paths_by_color(all_paths, attrs, config.get_color(value))
        print(f"There are {len(paths)} paths for value: {value}")          

        paths = merge_outer_and_hole_paths(paths)
        
        if (not paths): 
            print(f"no paths for value {value}. Continuing...")
            continue

        save_paths(
            paths,
            config.get_output_path(extension="_outlines"),
            svg_attrs,
            with_border=True,
            with_color=config.get_save_with_color()
        )

        max_area = config.get_max_area()
        min_area = config.get_min_area() 

        regular_paths = []
        small_paths = []
        large_paths = []
        paths_to_outline = []

        for path in paths: 
            poly = svgpath_to_shapely_polygon(path)
                    
            if min_area and poly.area < min_area: 
                print("skipping polygon - below configured min polygon area.")
                small_paths.append(path)
            elif max_area and poly.area > max_area:
                print("skipping polygon - above configured max polygon area.")
                large_paths.append(path)   
            else: 
                regular_paths.append(path)
        
        if config.get_outline_small_polygons(): 
            print("outlining too small polygons")        
            paths_to_outline.extend(small_paths)
        if (config.get_outline_regular_polygons()):
            print("outlining regular polygons")
            paths_to_outline.extend(regular_paths)
        if config.get_outline_large_polygons():
            print("outlining too large polygons")     
            paths_to_outline.extend(large_paths)
        
        for angle, step, slice_height in zip(angles, spacing, slice_flags):
            zigzags = paths_to_zigzag_paths(
                            regular_paths, 
                            angle, 
                            step, 
                            config,
                            slice_height=slice_height, 
                        )
            
            if (config.get_slice_large_polygons()):
                zigzags.extend(paths_to_zigzag_paths(
                                    large_paths, 
                                    angle, 
                                    step, 
                                    config, 
                                    slice_height=slice_height,
                                ))
                
            print(f"zigzags: {len(zigzags)}")
            zigzags_for_value.extend(zigzags)

        if not config.get_save_single_output():
            save_paths(
                remove_duplicate_paths(zigzags_for_value) + paths_to_outline,
                config.get_output_path(extension=f"[{value}]"),
                svg_attrs,
                with_border=True,
                with_color=config.get_save_with_color()
            )

    if config.get_save_single_output():
        all_combined = remove_duplicate_paths(zigzags_for_value)
        
        save_paths(
            all_combined + paths_to_outline,
            config.get_output_path(extension=(str(config.get_values_to_process()))),
            svg_attrs,
            with_border=True,
            with_color=config.get_save_with_color()
        )

if __name__ == "__main__":
    main()

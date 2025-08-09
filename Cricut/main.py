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
    cfg_filename = "config_quickmode.json"
    config = Config(cfg_filename)
    config.print_config()

    all_paths, attrs, svg_attrs = svg2paths2(os.path.join(config.get_input_path()))
    # Keep original outlines unmodified (do not remove hole paths yet)
    #save_paths(all_paths, config.get_output_path(extension="_outlines"), svg_attrs)
    zigzags_regular_size = []
    zigzags_small_size = []

    for value in config.get_values_to_process():
        if not config.get_save_single_output():
            zigzags_regular_size = []
            zigzags_small_size = []

        angles = config.get_angles(value)
        spacing = config.get_spacing(value)
        slice_flags = config.get_slice_sizes(value)
        paths = filter_paths_by_color(all_paths, attrs, config.get_color(value))
        print(f"There are {len(paths)} paths for value: {value}")

        paths = merge_outer_and_hole_paths(paths)

        
        max_area = 25000
        paths_to_use = []
        paths_to_outline = []
        for path in paths: 
            poly = svgpath_to_shapely_polygon(path)
            if poly.area > max_area:
                print("skip")
                paths_to_outline.append(path)
            else: 
                paths_to_use.append(path)
        
        if (not paths): 
            continue
        for angle, step, slice_height in zip(angles, spacing, slice_flags):
            zigzags_reg, zigzag_small = paths_to_zigzag_paths(
                paths_to_use, angle, step, slice_height=slice_height
            )
            print(f"small zigzags: {len(zigzag_small)}")
            print(f"reg zigzags: {len(zigzags_reg)}")
            zigzags_regular_size.extend(zigzags_reg)
            zigzags_small_size.extend(zigzag_small)

        # If you want a combined output per value (regular + small), merge and dedupe here:
        combined =  zigzags_regular_size #+ zigzags_small_size
        combined = remove_duplicate_paths(combined)      
            
        if not config.get_save_single_output():
            save_paths(
                combined + paths_to_outline,
                config.get_output_path(extension=f"_all_{value}"),
                svg_attrs,
                with_color=config.get_save_with_color()
            )

    if config.get_save_single_output():
        all_combined = remove_duplicate_paths( zigzags_regular_size + zigzags_small_size)
        
        save_paths(
            all_combined + paths_to_outline,
            config.get_output_path(extension="_all"),
            svg_attrs,
            with_color=config.get_save_with_color()
        )

if __name__ == "__main__":
    main()

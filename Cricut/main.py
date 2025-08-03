import os
from svgpathtools import svg2paths2
from path_utils import paths_to_zigzag_paths, filter_nested_paths, filter_paths_by_color, save_paths
from config import Config

def main():
    cfg_filename = "config.json"
    config = Config(cfg_filename)
    config.print_config()

    all_paths, attrs, svg_attrs = svg2paths2(os.path.join(config.get_input_path()))
    all_paths = filter_nested_paths(all_paths)
    save_paths(all_paths, config.get_output_path(extension="_outlines"), svg_attrs)
    
    zigzags_regular_size = []
    zigzags_small_size = []

    for value in config.get_values_to_process(): 
        angles = config.get_angles(value) 
        spacing = config.get_spacing(value)
        slice_flags = config.get_slice_sizes(value)
        paths = filter_paths_by_color(all_paths, attrs, config.get_color(value))

        for i in range(0, len(angles)): 
            zigzags_reg, zigzag_small = paths_to_zigzag_paths(paths, angles[i], spacing[i], slice_height=slice_flags[i])
            zigzags_small_size.extend(zigzag_small)
            print(f"small zigzags: {len(zigzag_small)}")
            print(f"reg zigzags: {len(zigzags_reg)}")
            zigzags_regular_size.extend(zigzags_reg)

    save_paths(zigzags_regular_size, config.get_output_path(extension="_regularpaths"), svg_attrs)
    save_paths(zigzags_small_size, config.get_output_path(extension="_smallpaths"), svg_attrs)

if __name__ == "__main__":
    main()
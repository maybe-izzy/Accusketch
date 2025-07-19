import os
import json
import os
from svgpathtools import svg2paths2, wsvg
from zigzag_fill import paths_to_zigzag_paths, random_color, get_border_path


class Config:
    def __init__(self, fname): 
        with open(fname) as f:
            self.cfg_dict = json.load(f)
    
    def get_svg_name(self): 
        return self.cfg_dict["svg_filename"]
        
    def get_values_to_process(self): 
        return self.cfg_dict["values_to_process"]
        
    def get_output_path(self): 
        return os.path.join("./svg/output/", self.get_svg_name())
        
    def get_input_path(self): 
        return os.path.join("./svg/input/", self.get_svg_name())
        
    def get_cmyk_value(self, value): 
        return self.cfg_dict["shading_config"][str(value)]["cmyk_str"]
        
    def get_angles(self, value): 
        return self.cfg_dict["shading_config"][str(value)]["angles"]
    
    def get_slice_sizes(self, value): 
        return self.cfg_dict["shading_config"][str(value)]["slice_heights"]
        
    def get_spacing(self, value): 
        return self.cfg_dict["shading_config"][str(value)]["spacing"]
        
    def get_all_values(self): 
        return self.cfg_dict["shading_config"].keys()
        
    def print_config(self):
        print(f"{'='*30} CONFIG {'='*30}")
        print(f"Input path: {self.get_input_path()}")
        print(f"Output path: {self.get_output_path()}") 
        for value in self.get_all_values():
            print(f"{value}\t:\tangles : {self.get_angles(value)}, slice_heights: {self.get_slice_sizes(value)}, spacing: {self.get_spacing(value)}")

def main():
    cfg_filename = "config.json"
    config = Config(cfg_filename)
    config.print_config()

    all_paths, attrs, svg_attrs = svg2paths2(os.path.join(config.get_input_path()))
    all_zigzags = []
    for value in config.get_values_to_process(): 
        angles = config.get_angles(value) 
        spacing = config.get_spacing(value)
        slice_flags = config.get_slice_sizes(value)
        
        for i in range(0, len(angles)): 
            all_zigzags.extend(paths_to_zigzag_paths(all_paths, angles[i], spacing[i], slice_height=slice_flags[i]))
  
    all_zigzags.extend(get_border_path(svg_attrs=svg_attrs))

    colors = [random_color() for _ in all_zigzags]

    wsvg(
        all_zigzags,
        filename=config.get_output_path(),
        svg_attributes=svg_attrs,
        colors=colors,
        stroke_widths=[0.1] * len(all_zigzags)
    )

if __name__ == "__main__":
    main()

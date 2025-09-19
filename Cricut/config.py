import os
import json

class Config:

    def __init__(self, config_filepath):
        with open(config_filepath) as f:
            self.cfg_dict = json.load(f)
            self.x_tolerance_epsilon = self.cfg_dict["x_tolerance_epsilon"]
            self.path_buffer =  self.cfg_dict["path_buffer"]
            self.overshoot =  self.cfg_dict["overshoot"]

    def get_save_single_output(self):
        return self.cfg_dict["save_single_output"]
    
    def get_svg_name(self):
        return self.cfg_dict["svg_filename"]

    def get_values_to_process(self):
        return self.cfg_dict["values_to_process"]

    def get_save_with_color(self):
        return self.cfg_dict["save_with_color"]

    def get_max_area(self): 
        return self.cfg_dict["max_polygon_area"]
    
    def get_min_area(self): 
        return self.cfg_dict["min_polygon_area"]
    
    def get_slice_large_polygons(self): 
        return self.cfg_dict["slice_large_polygons"]
    
    def get_slice_regular_polygons(self): 
        return self.cfg_dict["slice_regular_polygons"]
    
    def get_outline_large_polygons(self): 
        return self.cfg_dict["outline_large_polygons"]
    
    def get_outline_regular_polygons(self):
        return self.cfg_dict["outline_regular_polygons"]

    def get_outline_small_polygons(self): 
        return self.cfg_dict["outline_small_polygons"]
    
    def get_output_path(self, extension=None):
        if extension is None:
            return os.path.join(self.cfg_dict["svg_output_dir"],
                                (self.get_svg_name() + ".svg"))
        else:
            return os.path.join(self.cfg_dict["svg_output_dir"], 
                                (self.get_svg_name() + extension + ".svg"))

    def get_input_path(self):
        return os.path.join(self.cfg_dict["svg_input_dir"], self.get_svg_name() + ".svg")

    def get_color(self, value):
        return self.cfg_dict["shading_config"][str(value)]["color"]

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
            print(
                f"{value}\t:\tangles : {self.get_angles(value)}, slice_heights: {self.get_slice_sizes(value)}, spacing: {self.get_spacing(value)}"
            )

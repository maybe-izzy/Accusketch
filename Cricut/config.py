import os
import json

class Config:

    def __init__(self, fname):
        with open(fname) as f:
            self.cfg_dict = json.load(f)

    def get_save_single_output(self):
        return self.cfg_dict["save_single_output"]
    
    
    def get_outlines_only(self):
        return self.cfg_dict["outlines_only"]

    def get_save_with_color(self):
        return self.cfg_dict["save_with_color"]

    def get_svg_name(self):
        return self.cfg_dict["svg_filename"]

    def get_with_outline(self):
        return self.cfg_dict["with_outline"]

    def get_values_to_process(self):
        return self.cfg_dict["values_to_process"]

    def get_output_path(self, extension=None):
        if extension is None:
            return os.path.join("./svg/output/",
                                (self.get_svg_name() + ".svg"))
        else:
            return os.path.join("./svg/output/",
                                (self.get_svg_name() + extension + ".svg"))

    def get_input_path(self):
        return os.path.join("./svg/input/", self.get_svg_name() + ".svg")

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

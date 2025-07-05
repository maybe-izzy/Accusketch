from svgpathtools import svg2paths2, wsvg
from sketch_config import FILL_CONFIG, Value, FillStyle
from Cricut.fill_path_algorithms import zigzag, zigzag_crosshatch, straight_hatch_pass, straight_hatch

class SVGSketchProcessor:
    def __init__(self, input_file, output_file, shade: Value):
        self.input_file = input_file
        self.output_file = output_file
        self.config = FILL_CONFIG[shade]

    def applyShading(self):
        paths, attributes, svg_attrs = svg2paths2(self.input_file)
        new_paths = []

        for path in paths:
            if self.config.fill_style == FillStyle.STRAIGHT_HATCH:
                hatched = straight_hatch(
                                path,
                                self.config.line_spacing,
                                self.config.line_angles
                            )
                if hatched:
                    new_paths.extend(hatched)
            if self.config.fill_style == FillStyle.ZIGZAG_HATCH:
                hatched = zigzag(path, self.config.line_spacing, self.config.num_layers)
                if hatched:
                    new_paths.append(hatched)
            elif self.config.fill_style == FillStyle.ZIGZAG_CROSSHATCH:
                hatched = zigzag_crosshatch(path, self.config.line_spacing, self.config.num_layers)
                if hatched:
                    new_paths.append(hatched)
            else:
                continue
            
        if new_paths:
            wsvg(new_paths, filename=self.output_file, svg_attributes=svg_attrs)
        else:
            print("Warning: No paths were hatched.")



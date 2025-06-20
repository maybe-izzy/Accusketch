from svgpathtools import svg2paths2, wsvg
from sketch_config import FILL_CONFIG, Value, FillStyle
from fill_styles import zigzag, crosshatch, vertical, vertical_crosshatch

class SVGSketchProcessor:
    def __init__(self, input_file, output_file, shade: Value):
        self.input_file = input_file
        self.output_file = output_file
        self.settings = FILL_CONFIG[shade]

    def applyShading(self):
        paths, attributes, svg_attrs = svg2paths2(self.input_file)
        new_paths = []

        for path in paths:
            if self.settings.fill_style == FillStyle.VERTICAL:
                hatched = vertical(path, self.settings.line_spacing, 45)
                if hatched:
                    new_paths.extend(hatched)
            elif self.settings.fill_style == FillStyle.VERTICAL_CROSSHATCH:
                hatched = vertical_crosshatch(
                                path,
                                self.settings.line_spacing,
                                angle_deg_vertical=self.settings.line_angle_deg_vertical,
                                angle_deg_horizontal=self.settings.line_angle_deg_horizontal
                            )
                if hatched:
                    new_paths.extend(hatched)
                
            if self.settings.fill_style == FillStyle.ZIGZAG:
                hatched = zigzag(path, self.settings.line_spacing, self.settings.num_layers)
                if hatched:
                    new_paths.append(hatched)
            elif self.settings.fill_style == FillStyle.ZIGZAG_CROSSHATCH:
                hatched = crosshatch(path, self.settings.line_spacing, self.settings.num_layers)
                if hatched:
                    new_paths.append(hatched)
            else:
                continue
            
        if new_paths:
            wsvg(new_paths, filename=self.output_file, svg_attributes=svg_attrs)
        else:
            print("Warning: No paths were hatched.")



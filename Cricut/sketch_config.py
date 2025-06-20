from enum import Enum
from dataclasses import dataclass

class Value(Enum):
    L1 = 1
    L2 = 2

class FillStyle(Enum):
    VERTICAL = 1
    VERTICAL_CROSSHATCH = 2
    ZIGZAG = 3
    ZIGZAG_CROSSHATCH = 4

@dataclass
class Fill:
    line_spacing: float
    fill_style: FillStyle
    num_layers: int = 1
    line_angle_deg_vertical: float = 90
    line_angle_deg_horizontal: float = 0

FILL_CONFIG = {
    Value.L1: Fill(0.5, FillStyle.VERTICAL),
    Value.L2: Fill(3, FillStyle.ZIGZAG),
}

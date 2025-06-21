from enum import Enum
from dataclasses import dataclass, field
from typing import List

class Value(Enum):
    L1 = 1
    L1_25 = 2 
    L1_5 = 3
    L1_75 = 4
    L2 = 5
    L2_25 = 6
    L2_5 = 7
    L3 = 8
    L3_5 = 9 
    L4 = 10 
    L4_5 = 11
    L5 = 12 
    L5_5 = 13
    L6 = 14 
    L6_5 = 15
    L7 = 16
    L7_5 = 17
    L8 = 18
    L8_5 = 19
    L9 = 20
    L9_5 = 21
    L_10 = 22

class FillStyle(Enum):
    STRAIGHT_HATCH = 1
    ZIGZAG_HATCH = 2
    ZIGZAG_CROSSHATCH = 3

@dataclass
class Fill:
    line_spacing: float
    fill_style: FillStyle
    num_layers: int = 1 
    line_angles: List[float] = field(default_factory=list)

FILL_CONFIG = {
    Value.L1: Fill(0.5, FillStyle.ZIGZAG_HATCH, 1, [45, 135]),
    Value.L1_25: Fill(0.5, FillStyle.STRAIGHT_HATCH),
    Value.L1_5: Fill(0.5, FillStyle.STRAIGHT_HATCH),
    Value.L1_75: Fill(0.5, FillStyle.STRAIGHT_HATCH),
    Value.L2: Fill(0.5, FillStyle.STRAIGHT_HATCH),
    Value.L2_25: Fill(3, FillStyle.ZIGZAG_HATCH),
    Value.L2_5: Fill(3, FillStyle.ZIGZAG_HATCH),
    Value.L3: Fill(3, FillStyle.ZIGZAG_HATCH),
    Value.L3_5: Fill(3, FillStyle.ZIGZAG_HATCH),
    Value.L4: Fill(3, FillStyle.ZIGZAG_HATCH),
    Value.L4_5: Fill(3, FillStyle.ZIGZAG_HATCH),
    Value.L5: Fill(3, FillStyle.ZIGZAG_HATCH),
}

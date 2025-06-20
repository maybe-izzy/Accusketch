import os
from sketch_config import Value
from svg_processor import SVGSketchProcessor

def main():
    input_path = os.path.join("../svg", "b1.25.svg")
    output_path = os.path.join("../svg", "b1_hatched.svg")
    processor = SVGSketchProcessor(input_path, output_path, Value.L1)
    processor.applyShading()

if __name__ == "__main__":
    main()

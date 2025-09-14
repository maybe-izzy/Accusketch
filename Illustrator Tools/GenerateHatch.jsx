/*
 * hatchLayer.jsx — Illustrator 2025
 * ---------------------------------
 * Quickly covers the active artboard with evenly‑spaced, discrete hatch lines
 * on a layer named “Hatch”. There are **no clipping masks or groups**—each
 * line is its own simple PathItem so Cricut or laser software treats them as
 * strokes to draw.
 *
 * CONFIG — tweak values below or pass in new ones after running
 *   SPACING_PT     distance between lines (points)
 *   STROKE_PT      stroke width (points)
 *   ORIENTATION    "vertical" | "horizontal" | angle in degrees (number)
 *
 * Usage
 *   1. Open your document, select the artboard you want.
 *   2. File → Scripts → Other Script… → choose hatchLayer.jsx.
 *   3. A "Hatch" layer appears at the top with line segments spanning the
 *      artboard.
 */

(function hatchLayer() {
    if (!app.documents.length) {
        alert("Open a document first.");
        return;
    }

    /* ---- CONFIG ----------------------------------------------------- */
    var SPACING_PT  = 2;   // distance between lines (points)
    var STROKE_PT   = 0.25;  // stroke width (points)
    var ORIENTATION = "vertical"; // "vertical", "horizontal", or angle in °
    /* ----------------------------------------------------------------- */

    var doc   = app.activeDocument,
        idx   = doc.artboards.getActiveArtboardIndex(),
        rect  = doc.artboards[idx].artboardRect;   // [left, top, right, bottom]

    var left   = rect[0],
        top    = rect[1],
        right  = rect[2],
        bottom = rect[3];

    // Function to produce a solid black stroke in either RGB or CMYK docs
    function black() {
        if (doc.documentColorSpace === DocumentColorSpace.RGB) {
            var c = new RGBColor(); c.red = c.green = c.blue = 0; return c;
        } else {
            var k = new CMYKColor(); k.black = 100; return k;
        }
    }
    var BLACK = black();

    // Ensure we have a Hatch layer at the top
    var hatchLayer;
    try { hatchLayer = doc.layers.getByName("Hatch"); }
    catch (_) {
        hatchLayer = doc.layers.add();
        hatchLayer.name = "Hatch";
    }

    // Clear previous hatch lines if layer already had content
    while (hatchLayer.pageItems.length) hatchLayer.pageItems[0].remove();

    var count = 0;

    // Helper to add a line PathItem
    function addLine(x1, y1, x2, y2) {
        var dx = x2 - x1;
        var dy = y2 - y1;
        var length = Math.sqrt(dx * dx + dy * dy);
        var ux = dx / length;
        var uy = dy / length;

        // Perpendicular vector scaled by half the stroke width
        var px = -uy * STROKE_PT / 2;
        var py = ux * STROKE_PT / 2;

        // Four corners of the skinny rectangle
        var points = [
            [x1 + px, y1 + py],
            [x1 - px, y1 - py],
            [x2 - px, y2 - py],
            [x2 + px, y2 + py]
        ];

        var rect = hatchLayer.pathItems.add();
        rect.setEntirePath(points.concat([points[0]])); // close path
        rect.closed = true;
        rect.filled = true;
        rect.fillColor = BLACK;
        rect.stroked = false;

        count++;
    }

    if (typeof ORIENTATION === "string" && ORIENTATION.toLowerCase() === "horizontal") {
        // Horizontal hatch
        for (var y = top; y >= bottom - 0.01; y -= SPACING_PT) {
            addLine(left, y, right, y);
        }
    } else if (typeof ORIENTATION === "string" || ORIENTATION === 0 || ORIENTATION === "vertical") {
        // Vertical hatch (default)
        for (var x = left; x <= right + 0.01; x += SPACING_PT) {
            addLine(x, top, x, bottom);
        }
    } else {
        // Arbitrary angle — compute bounding box diagonal to be safe
        var radians = ORIENTATION * Math.PI / 180;
        var dx = Math.cos(radians), dy = Math.sin(radians);
        var diag = Math.sqrt(Math.pow(right - left, 2) + Math.pow(top - bottom, 2));
        // Vector perpendicular to hatch direction
        var pdx = -dy, pdy = dx;
        var steps = Math.ceil((pdx * (right - left) + pdy * (top - bottom)) / SPACING_PT) + 10;
        for (var i = -steps; i <= steps; i++) {
            var cx = (left + right) / 2 + i * SPACING_PT * pdx;
            var cy = (top + bottom) / 2 + i * SPACING_PT * pdy;
            addLine(cx - dx * diag, cy - dy * diag, cx + dx * diag, cy + dy * diag);
        }
    }

    alert("Hatch layer created: " + count + " lines at " + SPACING_PT + " pt spacing.");
})();
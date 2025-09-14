(function () {
    if (app.documents.length === 0) {
        alert("Open a document and select one shape with the fill color you want to match.");
        return;
    }

    var doc = app.activeDocument;
    var sel = doc.selection;

    if (!sel || sel.length !== 1) {
        alert("Please select exactly one shape as the color reference.");
        return;
    }

    var referenceItem = sel[0];
    var referenceColor = getFillColor(referenceItem);

    if (!referenceColor) {
        alert("Selected shape has no fill color.");
        return;
    }

    // Get Vertical Hatch source
    var hatchLayer;
    try {
        hatchLayer = doc.layers.getByName("Vertical Hatch");
    } catch (_) {
        alert("No layer named 'Vertical Hatch' found.");
        return;
    }

    if (hatchLayer.pageItems.length === 0) {
        alert("Vertical Hatch layer is empty.");
        return;
    }

    var hatchSource = hatchLayer.groupItems.length > 0
        ? hatchLayer.groupItems[0]
        : hatchLayer.pageItems[0];

    // Create result layer
    var resultLayer = doc.layers.add();
    resultLayer.name = "Hatched Output";

    // Gather matching items
    var matchingItems = [];
    for (var i = 0; i < doc.pageItems.length; i++) {
        var item = doc.pageItems[i];
        if (!item.locked && !item.hidden && hasSameFillColor(item, referenceColor)) {
            matchingItems.push(item);
        }
    }

    for (var j = 0; j < matchingItems.length; j++) {
        try {
            // Duplicate shape and hatch
            var original = matchingItems[j];
            var shapeCopy = original.duplicate(resultLayer, ElementPlacement.PLACEATEND);
            var hatchCopy = hatchSource.duplicate(resultLayer, ElementPlacement.PLACEATEND);

            // Flatten both
            var flattenedShape = flattenAndReturnPaths(shapeCopy);
            var flattenedHatch = flattenAndReturnPaths(hatchCopy);

            for (var s = 0; s < flattenedShape.length; s++) {
                for (var h = 0; h < flattenedHatch.length; h++) {
                    // Group pair of paths
                    var g = resultLayer.groupItems.add();
                    var shapePiece = flattenedShape[s].duplicate(g, ElementPlacement.PLACEATEND);
                    var hatchPiece = flattenedHatch[h].duplicate(g, ElementPlacement.PLACEATEND);

                    // Intersect the group
                    doc.selection = null;
                    g.selected = true;
                    app.executeMenuCommand("Live Pathfinder Intersect");
                    app.executeMenuCommand("expandStyle");
                    app.executeMenuCommand("ungroup");
                }
            }

        } catch (e) {
            $.writeln("Failed on item " + j + ": " + e);
        }
    }

    alert("Hatching complete.");

    // ---- HELPERS ----

    function getFillColor(item) {
        if (!item) return null;
        if (item.typename === "PathItem" && item.filled && item.fillColor.typename !== "NoColor") {
            return item.fillColor;
        }
        if (item.typename === "CompoundPathItem") {
            for (var i = 0; i < item.pathItems.length; i++) {
                var p = item.pathItems[i];
                if (p.filled && p.fillColor && p.fillColor.typename !== "NoColor") {
                    return p.fillColor;
                }
            }
        }
        return null;
    }

    function hasSameFillColor(item, refColor) {
        var fill = getFillColor(item);
        if (!fill || fill.typename !== refColor.typename) return false;

        if (fill.typename === "CMYKColor") {
            return fill.cyan === refColor.cyan &&
                fill.magenta === refColor.magenta &&
                fill.yellow === refColor.yellow &&
                fill.black === refColor.black;
        } else if (fill.typename === "RGBColor") {
            return fill.red === refColor.red &&
                fill.green === refColor.green &&
                fill.blue === refColor.blue;
        }
        return false;
    }

    function flattenAndReturnPaths(item) {
        var paths = [];

        if (item.typename === "PathItem") {
            paths.push(item);
        } else if (item.typename === "GroupItem") {
            for (var i = item.pageItems.length - 1; i >= 0; i--) {
                var child = item.pageItems[i];
                paths = paths.concat(flattenAndReturnPaths(child));
            }
            item.remove();
        } else if (item.typename === "CompoundPathItem") {
            for (var i = 0; i < item.pathItems.length; i++) {
                var sub = item.pathItems[i].duplicate(item.parent, ElementPlacement.PLACEATEND);
                paths.push(sub);
            }
            item.remove();
        }

        return paths;
    }
})();

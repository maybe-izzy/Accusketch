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

    var hatchGroup = hatchLayer.groupItems.length > 0
        ? hatchLayer.groupItems[0]
        : hatchLayer.pageItems[0];

    // Create result layer
    var resultLayer = doc.layers.add();
    resultLayer.name = "Hatched Output";

    // Iterate over all page items
    // First gather all items that match the fill color
var matchingItems = [];

for (var i = 0; i < doc.pageItems.length; i++) {
    var item = doc.pageItems[i];
    if (!item.locked && !item.hidden && hasSameFillColor(item, referenceColor)) {
        matchingItems.push(item);
    }
}

// Now loop over the *original* list only
for (var j = 0; j < matchingItems.length; j++) {
    var item = matchingItems[j];

    try {
        var shapeCopy = item.duplicate(resultLayer, ElementPlacement.PLACEATEND);
        var hatchCopy = hatchGroup.duplicate(resultLayer, ElementPlacement.PLACEATEND);

        var tempGroup = resultLayer.groupItems.add();
        shapeCopy.moveToBeginning(tempGroup);
        hatchCopy.moveToBeginning(tempGroup);

        doc.selection = null;
        tempGroup.selected = true;

        app.executeMenuCommand("Live Pathfinder Intersect");
        app.executeMenuCommand("expandStyle");
        app.executeMenuCommand("ungroup");

    } catch (e) {
        $.writeln("Error processing item: " + e);
    }
}

    alert("Hatch intersection complete.");

    // --------- Helpers ---------

    function getFillColor(item) {
        if (!item) return null;
    
        if (item.typename === "PathItem") {
            return (item.filled && item.fillColor.typename !== "NoColor") ? item.fillColor : null;
        }
    
        if (item.typename === "CompoundPathItem") {
            // Check all sub-paths inside the compound
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

        if (fill.typename === "RGBColor") {
            return fill.red === refColor.red &&
                fill.green === refColor.green &&
                fill.blue === refColor.blue;
        } else if (fill.typename === "CMYKColor") {
            return fill.cyan === refColor.cyan &&
                fill.magenta === refColor.magenta &&
                fill.yellow === refColor.yellow &&
                fill.black === refColor.black;
        } else if (fill.typename === "GrayColor") {
            return fill.gray === refColor.gray;
        } else if (fill.typename === "SpotColor") {
            return fill.spot.name === refColor.spot.name;
        }

        return false;
    }

    function forEachItem(collection, callback) {
        for (var i = 0; i < collection.length; i++) {
            callback(collection[i]);
        }
    }
})();

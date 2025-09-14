/**
 * Adobe Illustrator 2024 Script (ExtendScript)
 * 
 * This script:
 * 1. Requires one object to be selected.
 * 2. Duplicates (pastes in-place) the selected object onto a separate layer named "Red Layer".
 * 3. Changes the duplicated object's color to red.
 * 4. Turns off the visibility of all other layers.
 * 5. Adds a text box above the red object, displaying the original color's name if available (e.g., a spot swatch name),
 *    otherwise displaying "Red".
 * 
 * Notes:
 * - The script attempts to read a name from the object's fillColor or strokeColor if it's a SpotColor.
 *   If no name is found, "Red" is used.
 * - The "original color name" is determined by checking the object's fill and then stroke.
 *   If it was a SpotColor with a spot swatch name, that name will appear.
 * 
 * To run:
 * - Open a document in Illustrator.
 * - Select one object.
 * - Run this script from File > Scripts > Other Scripts...
 */

(function () {
    if (app.documents.length === 0) {
        alert("Please open a document and select an object first.");
        return;
    }
    var doc = app.activeDocument;
    var sel = doc.selection;
    if (!sel || sel.length === 0) {
        alert("Please select an object first.");
        return;
    }

    var selectedItem = sel[0];

    // Function to extract color name if it's a SpotColor
    function getColorName(color) {
        if (!color) return null;
        if (color.typename === "SpotColor" && color.spot && color.spot.name) {
            return color.spot.name;
        }
        return null;
    }

    // Try fill first, then stroke
    var originalColorName = getFillColor(selectedItem);

    // Create/find the "Red Layer"
    var redLayerName = "Red Layer";
    var redLayer = null;
    for (var i = 0; i < doc.layers.length; i++) {
        if (doc.layers[i].name === redLayerName) {
            redLayer = doc.layers[i];
            break;
        }
    }
    if (!redLayer) {
        redLayer = doc.layers.add();
        redLayer.name = redLayerName;
    }

    // Turn off visibility of all other layers
    for (var j = 0; j < doc.layers.length; j++) {
        var lyr = doc.layers[j];
        lyr.visible = (lyr.name === redLayerName);
    }

    // Duplicate the selected item into the red layer
    var duplicatedItem = selectedItem.duplicate(redLayer, ElementPlacement.INSIDE);

    // Change the duplicated object's color to pure red
    var newColor = new RGBColor();
    newColor.red = 255;
    newColor.green = 0;
    newColor.blue = 0;

    // Change fill color depending on object type
    if (duplicatedItem.typename === "TextFrame") {
        duplicatedItem.textRange.fillColor = newColor;
    } else if (duplicatedItem.typename === "PathItem") {
        duplicatedItem.fillColor = newColor;
    } else if (duplicatedItem.typename === "CompoundPathItem") {
        for (var pi = 0; pi < duplicatedItem.pathItems.length; pi++) {
            duplicatedItem.pathItems[pi].fillColor = newColor;
        }
    }


    //

    var item = sel[0];
    var fillColor = "None"; 
    
    if (!item.fillColor || item.fillColor.typename === "NoColor") {
        fillColor = getFillColor(item);
        if (!fillColor){
            alert("Selected object has no fill color.");
            return;
        }
    }
    else{
        fillColor = item.fillColor;
    }
    

    if (fillColor.typename === "CMYKColor") {
        // Extract CMYK values
        var c = Math.round(fillColor.cyan);
        var m = Math.round(fillColor.magenta);
        var y = Math.round(fillColor.yellow);
        var k = Math.round(fillColor.black);

        // Construct the CMYK key
        var cmykKey = "C=" + c + " M=" + m + " Y=" + y + " K=" + k;

        // Define the CMYK-to-key mapping
        var cmykMap = {
            "C=75 M=68 Y=67 K=90": "b1",
            "C=74 M=67 Y=66 K=85": "b1.25",
            "C=73 M=66 Y=65 K=80": "b1.5",
            "C=72 M=66 Y=65 K=75": "b1.75",
            "C=71 M=65 Y=64 K=70": "b2",
            "C=70 M=64 Y=63 K=64": "b2.25",
            "C=69 M=63 Y=62 K=59": "b2.5",
            "C=68 M=61 Y=60 K=47": "b3",
            "C=65 M=58 Y=57 K=38": "b3.5",
            "C=63 M=55 Y=54 K=29": "b4",
            "C=59 M=51 Y=51 K=21": "b4.5",
            "C=56 M=47 Y=47 K=13": "b5",
            "C=52 M=43 Y=43 K=9": "b5.5",
            "C=48 M=39 Y=40 K=4": "b6",
            "C=42 M=35 Y=35 K=2": "b6.5",
            "C=37 M=30 Y=30 K=0": "b7",
            "C=31 M=25 Y=25 K=0": "b7.5",
            "C=25 M=20 Y=20 K=0": "b8",
            "C=19 M=15 Y=16 K=0": "b8.5",
            "C=14 M=11 Y=11 K=0": "b9",
            "C=7 M=6 Y=6 K=0": "b9.5",
            "C=0 M=0 Y=0 K=0": "b10"
        };

        // Check if the CMYK key exists in the map
        if (cmykKey in cmykMap) {
            var value = cmykMap[cmykKey];
            var textItem = doc.textFrames.add();
            textItem.contents = value;
            textItem.textRange.size = 12; // Font size
            textItem.position = [item.position[0], item.position[1] + item.height]; // Slightly above the object
        } else {
            // Notify if no matching key is found
            alert("CMYK Key: " + cmykKey + "\nNo matching value found in the map.");
        }
      
    } else {
        alert("Selected object does not have a CMYK fill color.");
    }
})();


// Function to get the fill color of any object, including compound paths
function getFillColor(item) {
    if (item.typename === "PathItem") {
        return item.fillColor;
    } else if (item.typename === "CompoundPathItem") {
       
        for (var i = 0; i < item.pathItems.length; i++) {
            var pathColor = item.pathItems[i].fillColor;
            if (pathColor && pathColor.typename !== "NoColor") {
                return pathColor; // Return the first valid fill color found
            }
        }
    }
    return null;
}
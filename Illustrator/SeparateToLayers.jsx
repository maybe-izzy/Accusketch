/*
 * Separate Paths by Fill Color — Illustrator 2025
 * ------------------------------------------------
 * 
 * Run: File > Scripts > Other Script 
 */

(function () {
    if (!app.documents.length) {
        alert("No document open. Please open a document and try again.");
        return;
    }

    var doc = app.activeDocument;

    var logFile = (function () {
        var f = doc.saved ? File(doc.fullName.parent + "/output.txt")
                          : File(Folder.desktop + "/output.txt");
        if (!f.open("w")) {
            alert("Could not create output.txt (" + f.error + ").");
            throw new Error("Log file failure");
        }
        f.encoding = "UTF-8";
        return f;
    })();

    function log(line) { logFile.writeln(line); }
    log("Color‑Separation Report — " + new Date());
    log("Document: " + (doc.saved ? doc.fullName.name : "Untitled"));
    log("");

    function collectCompounds(container, bucket) {
        for (var i = 0; i < container.pageItems.length; i++) {
            var it = container.pageItems[i];
            if (it.typename === "CompoundPathItem") {
                bucket.push(it);
            } else if (it.typename === "GroupItem") {
                collectCompounds(it, bucket);
            }
        }
    }

    var compounds = [];
    for (var l = 0; l < doc.layers.length; l++) collectCompounds(doc.layers[l], compounds);

    compounds.sort(function (a, b) { return a.depth > b.depth ? -1 : 1; }); // deepest first

    var releasedCount = 0;
    for (var c = compounds.length - 1; c >= 0; c--) {
        var cp = compounds[c];
        try {
            cp.locked = cp.hidden = false;
            var parent = cp.parent;
            for (var p = cp.pathItems.length - 1; p >= 0; p--) {
                cp.pathItems[p].move(parent, ElementPlacement.PLACEATBEGINNING);
            }
            cp.remove();
            releasedCount++;
        } catch (e) {
            log("Error releasing compound path: " + e);
        }
    }
    log("Compound paths released: " + releasedCount);
    log("");


    var swatchMap = {
        "75_68_67_90": "b1",
        "74_67_66_85": "b1.25",
        "73_66_65_80": "b1.5",
        "72_66_65_75": "b1.75",
        "71_65_64_70": "b2",
        "70_64_63_64": "b2.25",
        "69_63_62_59": "b2.5",
        "68_61_60_47": "b3",
        "65_58_57_38": "b3.5",
        "63_55_54_29": "b4",
        "59_51_51_21": "b4.5",
        "56_47_47_13": "b5",
        "52_43_43_9":  "b5.5",
        "48_39_40_4":  "b6",
        "42_35_35_2":  "b6.5",
        "37_30_30_0":  "b7",
        "31_25_25_0":  "b7.5",
        "25_20_20_0":  "b8",
        "19_15_16_0":  "b8.5",
        "14_11_11_0":  "b9",
        "7_6_6_0":     "b9.5",
        "0_0_0_0":     "b10"
    };

    function colorKey(col) {
        if (col.typename === "CMYKColor") {
            var key = Math.round(col.cyan) + "_" + Math.round(col.magenta) + "_" + Math.round(col.yellow) + "_" + Math.round(col.black);
            return swatchMap[key] || "CMYK_" + key; // fallback to numeric name if no match
        } else if (col.typename === "SpotColor") {
            return "Spot_" + col.spot.name;
        } else if (col.typename === "RGBColor") {
            return "RGB_" + col.red + "_" + col.green + "_" + col.blue;
        } else if (col.typename === "GrayColor") {
            return "Gray_" + col.gray;
        }
        return "Color_Unknown";
    }

    function collectPaths(container, bucket) {
        for (var i = 0; i < container.pageItems.length; i++) {
            var it = container.pageItems[i];
            if (it.typename === "PathItem") {
                bucket.push(it);
            } else if (it.typename === "GroupItem") {
                collectPaths(it, bucket);
            }
        }
    }

    var allPaths = [];
    for (var ly = 0; ly < doc.layers.length; ly++) collectPaths(doc.layers[ly], allPaths);

    var layerMap = {}; 
    var counts = {};

    for (var idx = 0; idx < allPaths.length; idx++) {
        var path = allPaths[idx];
        if (!path.filled) continue; 

        var key = colorKey(path.fillColor);

        var lay = layerMap[key];
        if (!lay) {
            if (doc.layers[0].name === key) {
                lay = doc.layers[0]; 
            } else {
                lay = doc.layers.add();
                lay.name = key;
            }
            layerMap[key] = lay;
            counts[key] = 0;
        }

        try {
            path.duplicate(lay, ElementPlacement.PLACEATBEGINNING);
            counts[key]++;
        } catch (e) {
            log("Failed duplicating path to layer " + key + ": " + e);
        }
    }

    log("Color layer breakdown:");
    for (var k in counts) {
        log("  • " + k + ": " + counts[k] + " paths");
    }
    logFile.close();

    var bLayers = [];
    for (var name in layerMap) {
        var match = name.match(/^b(\d+(\.\d+)?)/);
        if (match) {
            bLayers.push({ name: name, value: parseFloat(match[1]), layer: layerMap[name] });
        }
    }
    bLayers.sort(function (a, b) { return a.value - b.value; });
    for (var i = 0; i < bLayers.length; i++) {
        bLayers[i].layer.zOrder(ZOrderMethod.SENDTOBACK);
    }

    alert("Finished separating paths by fill color.\nReport saved to " + logFile.fsName);
})();

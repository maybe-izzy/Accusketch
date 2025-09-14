function distance(p1, p2) {
    return Math.sqrt(Math.pow(p1[0] - p2[0], 2) + Math.pow(p1[1] - p2[1], 2));
}

function getOrderedPointsFromOutline(pathItem) {
    var dup = pathItem.duplicate();
    dup.filled = false;
    dup.stroked = true;
    dup.strokeWidth = 0.1;
    dup.selected = true;

    app.executeMenuCommand("outline");

    var sel = app.activeDocument.selection;
    var result = [];

    if (sel.length > 0 && sel[0].pathPoints) {
        var pts = sel[0].pathPoints;
        for (var i = 0; i < pts.length; i++) {
            var pt = pts[i].anchor;
            result.push([pt[0], pt[1]]);
        }
        sel[0].remove();
    }

    return result;
}

function drawAcrossLines(pathItem, numLines) {
    var doc = app.activeDocument;
    var layer = doc.activeLayer;

    var points = getOrderedPointsFromOutline(pathItem);
    var total = points.length;

    var half = Math.floor(total / 2);
    var top = points.slice(0, half);
    var bottom = points.slice(half).concat(points.slice(0, 1));

    var step = Math.min(top.length, bottom.length) / numLines;

    for (var i = 0; i < numLines; i++) {
        var idx1 = Math.floor(i * step);
        var idx2 = Math.floor(bottom.length - 1 - i * step);

        if (top[idx1] && bottom[idx2]) {
            var line = layer.pathItems.add();
            line.setEntirePath([top[idx1], bottom[idx2]]);
            line.stroked = true;
            line.filled = false;
            line.strokeWidth = 0.5;
        }
    }
}

function main() {
    if (app.documents.length === 0 || app.activeDocument.selection.length === 0) {
        alert("Select one closed path.");
        return;
    }

    var path = app.activeDocument.selection[0];
    if (!path.closed || path.pathPoints.length < 3) {
        alert("Path must be closed and have at least 3 points.");
        return;
    }

    var numLines = 100; // Adjust the number of lines to draw across
    drawAcrossLines(path, numLines);
}

main();
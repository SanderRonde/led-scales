baseLength = 25; // [30:1:50]
baseWidth = 2; // [2:1:10]
tipWidth = 5; // [2:1:10]
baseHeight = 110; // [100:1:250]
spikeSize = 50; // [50:1:100]

spacing = 55; // [50:1:100]
xCount = 6; // [6:2:20]
yCount = 12; // [6:2:20]

leanBase = 5; // [0:1:10]
leanFactor = 0.05; // [0.01:0.01:0.1]

panelCount = 3; // [1:2:9]
panelSpacing = 80; // [0:1:100]

ledDiameter = 10; // [1:1:20]
is2D = false; // [true, false]
isFast = false; // [true, false]

estimatedWeightG = 23/2; // [10:1:500]
pricePerKilo = 20; // [10:1:100]

// TODO:(sander) consider:
// Log every possible `distance`
// Calculate anew using every `distance` but sort of order this array
// Then do tiling

isPrint = true; // [true, false]
printBedSpacing = 400; // [100:1:500]
xPerBuildPlate = 5;
yPerBuildPlate = 5;

spikeHeight = baseHeight - spikeSize;

finalSpacing = isPrint ? ((sqrt(baseLength * baseLength + baseLength * baseLength)) + 5) : spacing;
finalPanelSpacing = isPrint ? 0 : panelSpacing;

module scaleHalf(isRotated) {
    translate([0, 0, -spikeHeight]) {
        cube([baseLength, baseWidth, spikeHeight]);
    };
    cube([baseLength, baseWidth, spikeHeight]);
    translate([0, baseWidth, spikeHeight])
        rotate([90, 0, 0])
            linear_extrude(height=baseWidth)
                polygon(points=[[0,0], [baseLength,0], [tipWidth, spikeHeight]], paths=[[0,1,2]]);
    translate([0, 0, spikeHeight])
    cube([tipWidth, tipWidth, spikeHeight]);
}

module scale3D(distance) {
    distanceFromCenter = sqrt(baseLength);
    sizeOfScale = baseLength + baseWidth;
    leanAngle = leanBase + (distance * leanFactor);
    translate([-sqrt(sizeOfScale * sizeOfScale / 2), 0, 0]) {
        rotate([0, -leanAngle, 0]) {
            rotate([0, 0, -45]) {
                scaleHalf();
            }
            translate([sqrt(baseWidth), sqrt(baseWidth), 0])
            translate([0, -(baseWidth * sqrt(2)), 0])
            rotate([-0, 0, 45]) {
                scaleHalf();
            }
        }
    }
}



module scale(distance) {
    if (is2D) {
        translate([0, 0, 0]) {
            circle(d=ledDiameter);
        }
        projection(cut=true) {
            scale3D(distance);
        };
    } else {
        scale3D(distance);
    }
}

module drawPanel(scaleXOffset, scaleYOffset) {
    for (_i = [-xCount / 2:1:xCount / 2]) {
        i = _i + scaleXOffset;
        for (_j = [-yCount / 2:1:yCount / 2]) {
            j = _j + scaleYOffset;
            distance = sqrt(i*i + j*j) * finalSpacing;
            translate([-(i * finalSpacing) - (finalSpacing / 2), -(j * finalSpacing), 0]) {
                rotate([0, 0, isPrint ? 0 : atan2(j, i + 0.5)])
                scale(distance);
            }
            translate([-(i * finalSpacing), -(j * finalSpacing) - (finalSpacing / 2), 0]) {
                rotate([0, 0, isPrint ? 0 : atan2(j + 0.5, i)])
                scale(distance);
            };
        }
    }
}

totalWidth = (xCount + 1) * finalSpacing * panelCount + (finalPanelSpacing * (panelCount - 1));
totalHeight = (yCount + 1) * finalSpacing;
if (isPrint) {
    totalPerBuildPlate = xPerBuildPlate * yPerBuildPlate;
    echo("xPerBuildPlate is ", xPerBuildPlate);
    echo("yPerBuildPlate is ", yPerBuildPlate);
    echo("totalPerBuildPlate is ", totalPerBuildPlate);

    difference() {
        union() {
            for (p = [0:1:((panelCount - 1) / 2)]) {
                for (invert = [-1, 1]) {
                    for (_i = [-xCount / 2:1:xCount / 2]) {
                        i = _i + (invert  * p * xCount);
                        for (j = [-yCount / 2:1:yCount / 2]) {
                            distance = sqrt(i*i + j*j) * finalSpacing;

                            totalCount = (p * 2 * (xCount + 1) * (yCount + 1)) + 
                                ((invert + 1) / 2 * (xCount + 1) * (yCount + 1)) + 
                                ((_i + xCount / 2) * (yCount + 1)) + 
                                (j + yCount / 2);

                            buildPlateIndex = floor(totalCount / totalPerBuildPlate);
                            remainder = totalCount % totalPerBuildPlate;
                            buildPlateX = floor(remainder / xPerBuildPlate);
                            buildPlateY = remainder % xPerBuildPlate;

                            translate([(buildPlateIndex * printBedSpacing) -(buildPlateX * finalSpacing) - (finalSpacing / 2), -(buildPlateY * finalSpacing), 0]) {
                                rotate([0, 0, isPrint ? 0 : atan2(j, i + 0.5)])
                                scale(distance);
                            }
                            translate([(buildPlateIndex * printBedSpacing) -(buildPlateX * finalSpacing), -(buildPlateY * finalSpacing), 0]) {
                                rotate([0, 0, isPrint ? 0 : atan2(j, i + 0.5)])
                                scale(distance);
                            };
                        }
                    }
                }
            }
        }
        translate([(-totalWidth / 2) * 1.5, (-totalHeight / 2) * 1.5, -baseHeight * 1.5]) {
            cube([totalWidth * 50, totalHeight * 1.5, baseHeight * 1.5]);
        }
    }
} else {
    difference() {
        union() {
            drawPanel(0, 0, xCount, yCount);
            for (i = [1:1:((panelCount - 1) / 2)]) {
                translate([-i * finalPanelSpacing, 0, 0]) {
                    drawPanel(((i) * xCount) + 1, 0, xCount, yCount);
                };
                translate([i * finalPanelSpacing, 0, 0]) {
                    drawPanel(-(i * xCount) - 1, 0, xCount, yCount);
                };
            }
        }
        if (!isFast) {
            translate([(-totalWidth / 2) * 1.5, (-totalHeight / 2) * 1.5, -baseHeight * 1.5]) {
                cube([totalWidth * 1.5, totalHeight * 1.5, baseHeight * 1.5]);
            }
        }
    }
}

echo("Panel dimensions are ", totalWidth, "x", totalHeight);
echo("Panel count is ", panelCount);
echo("Total width is ", totalWidth);
echo("Scale count is ", xCount * yCount * panelCount);
echo("Estimated weight is ", estimatedWeightG * xCount * yCount * panelCount / 1000, "kg");
echo("Estimated price is €", estimatedWeightG * xCount * yCount * panelCount / 1000 * pricePerKilo);

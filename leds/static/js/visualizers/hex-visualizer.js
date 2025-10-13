import { LEDVisualizerBase } from "./visualizer-base.js";

/**
 * @typedef {Object} Hexagon
 * @property {number} x - X coordinate
 * @property {number} y - Y coordinate
 * @property {number[]} ordered_leds - Array of LED indices
 */

/**
 * @typedef {Object} HexConfig
 * @property {'hex'} type - Type of visualizer
 * @property {number} hex_size - Size of each hexagon
 * @property {Hexagon[]} hexagons - Array of hexagons
 * @property {number} max_x - Maximum x coordinate
 * @property {number} max_y - Maximum y coordinate
 */

/**
 * Class representing the LED Visualizer
 */
export class HexLEDVisualizer extends LEDVisualizerBase {
    /** @param {HexConfig} config */
    constructor(config) {
        super();

        /** @type {HexConfig} */
        this.config = config;
    }

    /**
     * Draws a simple hexagon at the specified position
     * @param {number} x - X coordinate of center
     * @param {number} y - Y coordinate of center
     * @param {number} hexIndex - Index of the hexagon
     * @param {import("./visualizer-base.js").LED[][]} pixelStrips - The pixel data received from the server
     * @param {number} scale - Scale factor
     */
    drawHexagon(x, y, hexIndex, pixelStrips, scale) {
        this.ctx.save();
        this.ctx.beginPath();

        // Calculate the points of the hexagon
        for (let i = 0; i < 6; i++) {
            const angle = (i * Math.PI * 2) / 6;
            const pointX =
                x + Math.cos(angle) * (this.config.hex_size / 2) * scale;
            const pointY =
                y + Math.sin(angle) * (this.config.hex_size / 2) * scale;

            if (i === 0) {
                this.ctx.moveTo(pointX, pointY);
            } else {
                this.ctx.lineTo(pointX, pointY);
            }
        }

        // Draw a circle with radius hex_size/2
        this.ctx.closePath();
        this.ctx.lineWidth = 1;
        this.ctx.strokeStyle = `rgb(255, 255, 255)`;
        this.ctx.stroke();

        for (
            let i = 0;
            i < this.config.hexagons[hexIndex].ordered_leds.length;
            i++
        ) {
            const angle =
                ((this.config.hexagons[hexIndex].ordered_leds.length - i) *
                    Math.PI *
                    2) /
                    this.config.hexagons[hexIndex].ordered_leds.length +
                Math.PI / 2;
            const ledRadius = (this.config.hex_size / 2) * 0.8;
            const pointX = x + Math.cos(angle) * ledRadius * scale;
            const pointY = y + Math.sin(angle) * ledRadius * scale;

            this.ctx.beginPath();
            this.ctx.arc(
                pointX,
                pointY,
                this.config.hex_size * scale * 0.03,
                0,
                Math.PI * 2
            );
            const ledIndex = this.config.hexagons[hexIndex].ordered_leds[i];
            // Apply brightness to RGB values
            const brightness = pixelStrips[0][ledIndex].brightness / 255; // Default to 1.0 if not provided
            if (
                pixelStrips[0][ledIndex].x !== undefined &&
                pixelStrips[0][ledIndex].y !== undefined
            ) {
                this.ctx.font = "6px Arial";
                this.ctx.fillStyle = "white";
                this.ctx.fillText(
                    `(${pixelStrips[0][ledIndex].x.toFixed(
                        1
                    )}, ${pixelStrips[0][ledIndex].y.toFixed(1)})`,
                    pointX,
                    pointY
                );
            } else {
                this.ctx.fillStyle = `rgb(${
                    pixelStrips[0][ledIndex].r * brightness
                }, ${pixelStrips[0][ledIndex].g * brightness}, ${
                    pixelStrips[0][ledIndex].b * brightness
                })`;
                this.ctx.fill();
            }
        }
        this.ctx.restore();
    }

    /**
     * Updates all LEDs by receiving pixel data from the WebSocket server and redrawing
     * @param {import("./visualizer-base.js").LED[][]} pixelStrips - The pixel data received from the server
     * @param {number} scale - Scale factor
     */
    updateLEDsWithData(pixelStrips, scale) {
        for (
            let hexIndex = 0;
            hexIndex < this.config.hexagons.length;
            hexIndex++
        ) {
            const hexagon = this.config.hexagons[hexIndex];
            const hexSize = this.config.hex_size * scale;
            const centerX = (hexagon.x + 0.5) * hexSize * 0.8 + 0.1 * hexSize;
            const centerY =
                this.canvas.height - (hexagon.y + 0.5) * hexSize * 0.9;

            // Draw a simple hexagon for now
            this.drawHexagon(centerX, centerY, hexIndex, pixelStrips, scale);
        }
    }

    getDimensions() {
        return {
            width: this.config.max_x * 1.05,
            height: this.config.max_y,
        };
    }
}

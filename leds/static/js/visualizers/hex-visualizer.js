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
                (i * Math.PI * 2) /
                this.config.hexagons[hexIndex].ordered_leds.length;
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
            const brightness = pixelStrips[ledIndex].brightness / 255; // Default to 1.0 if not provided
            this.ctx.fillStyle = `rgb(${
                pixelStrips[ledIndex].r * brightness
            }, ${pixelStrips[ledIndex].g * brightness}, ${
                pixelStrips[ledIndex].b * brightness
            })`;
            this.ctx.fill();
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
            const centerX = (hexagon.x + 0.5) * this.config.hex_size * scale;
            const centerY =
                this.canvas.height -
                (hexagon.y + 0.5) * this.config.hex_size * scale;

            // Draw a simple hexagon for now
            this.drawHexagon(centerX, centerY, hexIndex, pixelStrips, scale);
        }
    }

    getDimensions() {
        return {
            width: this.config.max_x,
            height: this.config.max_y,
        };
    }
}

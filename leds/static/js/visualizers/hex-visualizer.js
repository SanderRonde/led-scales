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
     * Draws a single LED at the specified position with the given color
     * @param {number} index - LED index
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     * @param {{r: number, g: number, b: number, w?: number}} color - RGB color object
     * @param {number} scale - Scale factor
     * @param {Config} config - Configuration object
     */
    drawScale(index, x, y, color, scale, config) {
        // Calculate angle towards the center
        const centerX = config.total_width / 2;
        const centerY = config.total_height / 2 + config.scale_length / 2;

        //  // Draw the LED index as text
        // this.ctx.save();
        // this.ctx.font = `${10 * scale}px Arial`;
        // this.ctx.fillStyle = "#FFFFFF";
        // this.ctx.textAlign = "center";
        // this.ctx.textBaseline = "middle";
        // this.ctx.fillText(index.toString(), x * scale, y * scale);
        // this.ctx.restore();

        // Calculate the angle from the LED position to the center
        const dx = centerX - x;
        const dy = centerY - y;
        const angle = Math.atan2(dy, dx);

        // Subtract 45 degrees (π/4 radians)
        const adjustedAngle = angle - Math.PI / 4;

        // Draw scale itself
        this.ctx.save();
        const offset =
            Math.sqrt((config.scale_length * config.scale_length) / 2) /
            Math.sqrt(2);
        // First translate to the LED center point
        this.ctx.translate(x * scale, y * scale);
        // Then rotate around this center point
        this.ctx.rotate(adjustedAngle);
        // Then translate by the offset to position the scale correctly
        this.ctx.translate(-offset, -offset);

        // Draw horizontal part of the scale
        this.ctx.beginPath();
        this.ctx.rect(
            0,
            0,
            config.scale_length * scale,
            config.scale_width * scale
        );
        this.ctx.fillStyle = `#FFFFFF`;
        this.ctx.fill();

        // Draw vertical part of the scale
        this.ctx.beginPath();
        this.ctx.rect(
            0,
            0,
            config.scale_width * scale,
            config.scale_length * scale
        );
        this.ctx.fillStyle = `#FFFFFF`;
        this.ctx.fill();

        this.ctx.restore();

        // Draw LED
        this.ctx.beginPath();
        this.ctx.arc(x * scale, y * scale, 5 * scale, 0, Math.PI * 2);
        this.ctx.fillStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
        this.ctx.fill();
    }

    /**
     * Draws a simple hexagon at the specified position
     * @param {number} x - X coordinate of center
     * @param {number} y - Y coordinate of center
     * @param {number} hexIndex - Index of the hexagon
     * @param {Array<Array<{r: number, g: number, b: number, w?: number}>>} pixelStrips - The pixel data received from the server
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

            this.ctx.fillStyle = `rgb(${pixelStrips[ledIndex].r}, ${pixelStrips[ledIndex].g}, ${pixelStrips[ledIndex].b})`;
            this.ctx.fill();
        }
        this.ctx.restore();
    }

    /**
     * Updates all LEDs by receiving pixel data from the WebSocket server and redrawing
     * @param {Array<Array<{r: number, g: number, b: number, w?: number}>>} pixelStrips - The pixel data received from the server
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

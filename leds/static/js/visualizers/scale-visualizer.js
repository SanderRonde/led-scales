import { LEDVisualizerBase } from "./visualizer-base.js";

/**
 * @typedef {Object} ScaleConfig
 * @property {'scale'} type - Type of visualizer
 * @property {number} x_count - Number of scales in x direction per panel
 * @property {number} y_count - Number of scales in y direction
 * @property {number} panel_count - Number of panels
 * @property {number} spacing - Spacing between scales
 * @property {number} total_width - Total width of all panels
 * @property {number} total_height - Total height of all panels
 * @property {number} panel_spacing_scales - Spacing between panels in scale units
 * @property {number} scale_length - Length of each scale
 * @property {number} scale_width - Width of each scale
 * @property {number} delay - Delay between updates in milliseconds
 */

/**
 * Class representing the LED Visualizer
 */
export class ScaleLEDVisualizer extends LEDVisualizerBase {
    /** @param {ScaleConfig} config */
    constructor(config) {
        super();

        /** @type {ScaleConfig} */
        this.config = config;
    }

    /**
     * Draws a single LED at the specified position with the given color
     * @param {number} index - LED index
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     * @param {import("./visualizer-base.js").LED} color - RGB color object
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
        // Apply brightness to RGB values
        const brightness = color.brightness / 255; // Default to 1.0 if not provided
        this.ctx.fillStyle = `rgb(${color.r * brightness}, ${
            color.g * brightness
        }, ${color.b * brightness})`;
        this.ctx.fill();
    }

    /**
     * Updates all LEDs by receiving pixel data from the WebSocket server and redrawing
     * @param {import("./visualizer-base.js").LED[][]} pixelStrips - The pixel data received from the server
     * @param {number} scale - Scale factor
     */
    updateLEDsWithData(pixelStrips, scale) {
        for (let panel = 0; panel < this.config.panel_count; panel++) {
            let pixelIndex = 0;
            const panelOffsetX =
                panel *
                    (this.config.x_count * this.config.spacing +
                        this.config.spacing) +
                this.config.spacing / 2;

            for (let x = 0; x < this.config.x_count; x++) {
                // Draw row from bottom to top
                for (let y = 0; y < this.config.y_count; y++) {
                    if (pixelIndex < pixelStrips[panel].length) {
                        this.drawScale(
                            pixelIndex,
                            panelOffsetX + x * this.config.spacing,
                            this.config.total_height -
                                (y + 1) * this.config.spacing,
                            pixelStrips[panel][pixelIndex],
                            scale,
                            this.config
                        );
                        pixelIndex++;
                    }
                }

                // Then draw row from top to bottom
                if (x !== this.config.x_count - 1) {
                    for (let y = this.config.y_count - 1; y >= 0; y--) {
                        if (pixelIndex < pixelStrips[panel].length) {
                            this.drawScale(
                                pixelIndex,
                                panelOffsetX +
                                    x * this.config.spacing +
                                    this.config.spacing / 2,
                                this.config.total_height -
                                    y * this.config.spacing -
                                    this.config.spacing / 2,
                                pixelStrips[panel][pixelIndex],
                                scale,
                                this.config
                            );
                            pixelIndex++;
                        }
                    }
                }
            }
        }
    }

    getDimensions() {
        return {
            width: this.config.total_width,
            height: this.config.total_height,
        };
    }
}

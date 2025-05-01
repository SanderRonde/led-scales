/**
 * Class representing the LED Visualizer
 */
class LEDVisualizer {
    /**
     * Create a new LED Visualizer
     */
    constructor() {
        this.canvas = document.getElementById("canvas");
        /** @type {CanvasRenderingContext2D} */
        this.ctx = this.canvas.getContext("2d");

        /**
         * @typedef {Object} Config
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

        /** @type {Config} */
        this.config = null;

        /** @type {WebSocket} */
        this.socket = null;

        // Bind methods to this instance
        this.calculateScale = this.calculateScale.bind(this);
        this.updateCanvasSize = this.updateCanvasSize.bind(this);
        this.drawScale = this.drawScale.bind(this);
        this.updateLEDsWithData = this.updateLEDsWithData.bind(this);
        this.resizeCanvas = this.resizeCanvas.bind(this);

        // Add event listeners
        window.addEventListener("resize", this.resizeCanvas);
        this.resizeCanvas();
    }

    /**
     * Calculates the appropriate scale factor based on window dimensions
     * @returns {number} The scale factor to use
     */
    calculateScale() {
        const BASE_SCALE = 2; // Base scale factor for better visibility
        const MARGIN = 0.1; // 10% margin on each side

        // Calculate the maximum width and height that would fit in the window
        const maxWidth = window.innerWidth * (1 - 2 * MARGIN);
        const maxHeight = window.innerHeight * (1 - 2 * MARGIN);

        // Calculate the required width and height based on config
        const requiredWidth =
            this.config.x_count *
                this.config.spacing *
                this.config.panel_count +
            this.config.spacing * (this.config.panel_count - 1);
        const requiredHeight = this.config.y_count * this.config.spacing;

        // Calculate scale factors for width and height
        const widthScale = maxWidth / requiredWidth;
        const heightScale = maxHeight / requiredHeight;

        // Use the smaller scale to ensure everything fits
        return Math.min(widthScale, heightScale, BASE_SCALE);
    }

    /**
     * Updates the canvas size based on current window dimensions
     */
    updateCanvasSize() {
        const scale = this.calculateScale();
        this.canvas.width = this.config.total_width * scale;
        this.canvas.height = this.config.total_height * scale;
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
     * Updates all LEDs by receiving pixel data from the WebSocket server and redrawing
     * @param {Array<Array<{r: number, g: number, b: number, w?: number}>>} pixelStrips - The pixel data received from the server
     */
    updateLEDsWithData(pixelStrips) {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        const scale = this.calculateScale();
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

    /**
     * Initializes the visualizer by fetching configuration and setting up the canvas
     * @async
     * @returns {Promise<void>}
     */
    async initialize() {
        try {
            // Get configuration from server
            this.config = await fetch("/config").then((response) => {
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}`);
                }
                return response.json();
            });

            // Set initial canvas size
            this.updateCanvasSize();

            // Add resize handler
            window.addEventListener("resize", this.updateCanvasSize);

            // Initialize WebSocket connection
            this.socket = io();
            this.socket.on("connect", () => {
                console.log("Connected to WebSocket server");
            });
            this.socket.on("disconnect", () => {
                console.log("Disconnected from WebSocket server");
                // Display error message on canvas
                this.ctx.font = "16px Arial";
                this.ctx.fillStyle = "red";
                this.ctx.fillText("Connection lost. Retrying...", 20, 50);
            });
            this.socket.on("led_update", (data) => {
                this.updateLEDsWithData(data);
            });
        } catch (error) {
            console.error("Failed to initialize visualizer:", error);

            // Set a basic canvas size for error display
            this.canvas.width = window.innerWidth * 0.8;
            this.canvas.height = window.innerHeight * 0.8;

            // Display error message on canvas
            this.ctx.font = "16px Arial";
            this.ctx.fillStyle = "red";
            this.ctx.fillText(
                "Failed to connect to server. Retrying in 5 seconds...",
                20,
                50
            );

            // Retry initialization after 5 seconds
            setTimeout(() => this.initialize(), 5000);
        }
    }

    /**
     * Resizes the canvas to fit its container
     */
    resizeCanvas() {
        const container = this.canvas.parentElement;
        this.canvas.width = container.clientWidth;
        this.canvas.height = container.clientHeight;
    }
}

// Create and export the visualizer instance
const visualizer = new LEDVisualizer();

/**
 * Initializes the visualizer by fetching configuration and setting up the canvas
 * @async
 * @returns {Promise<void>}
 */
export async function initializeVisualizer() {
    await visualizer.initialize();
}

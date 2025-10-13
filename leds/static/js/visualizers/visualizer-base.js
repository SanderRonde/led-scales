/**
 * @typedef {Object} LED
 * @property {number} r - Red value
 * @property {number} g - Green value
 * @property {number} b - Blue value
 * @property {number} w - White value
 * @property {number} brightness - Brightness value [0-255]
 * @property {number} [x] - X coordinate (only present if debug_positions is enabled)
 * @property {number} [y] - Y coordinate (only present if debug_positions is enabled)
 */

/**
 * Base class representing the LED Visualizer
 */
export class LEDVisualizerBase {
    /**
     * Create a new LED Visualizer
     */
    constructor() {
        this.canvas = document.getElementById("canvas");
        /** @type {CanvasRenderingContext2D} */
        this.ctx = this.canvas.getContext("2d");

        /** @type {WebSocket} */
        this.socket = null;

        // Bind methods to this instance
        this.calculateScale = this.calculateScale.bind(this);
        this.updateCanvasSize = this.updateCanvasSize.bind(this);
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

        // Calculate scale factors for width and height
        const { width, height } = this.getDimensions();
        const widthScale = maxWidth / width;
        const heightScale = maxHeight / height;

        // Use the smaller scale to ensure everything fits
        return Math.min(widthScale, heightScale, BASE_SCALE);
    }

    /**
     * Updates the canvas size based on current window dimensions
     */
    updateCanvasSize() {
        const scale = this.calculateScale();
        const dimensions = this.getDimensions();
        this.canvas.width = dimensions.width * scale;
        this.canvas.height = dimensions.height * scale;
    }

    /**
     * Updates all LEDs by receiving pixel data from the WebSocket server and redrawing
     * @abstract
     * @returns {{width: number, height: number}} The dimensions of the visualizer
     * @throws {Error} Should be implemented by subclasses
     */
    getDimensions() {
        throw new Error(
            "Method getDimensions() must be implemented by subclass"
        );
    }

    /**
     * Updates all LEDs by receiving pixel data from the WebSocket server and redrawing
     * @abstract
     * @param {LED[][]} pixelStrips - The pixel data received from the server
     * @throws {Error} Should be implemented by subclasses
     */
    updateLEDsWithData(pixelStrips, scale) {
        throw new Error(
            "Method updateLEDsWithData() must be implemented by subclass"
        );
    }

    /**
     * Initializes the visualizer by fetching configuration and setting up the canvas
     * @async
     * @returns {Promise<void>}
     */
    async initialize() {
        try {
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
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                const scale = this.calculateScale();
                /** @type {LED[][]} */
                const typedData = data;
                this.updateLEDsWithData(typedData, scale);
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

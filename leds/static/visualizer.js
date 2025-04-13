const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

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
let config = null;

/**
 * Calculates the appropriate scale factor based on window dimensions
 * @returns {number} The scale factor to use
 */
function calculateScale() {
    const BASE_SCALE = 2; // Base scale factor for better visibility
    const MARGIN = 0.1; // 10% margin on each side

    // Calculate the maximum width and height that would fit in the window
    const maxWidth = window.innerWidth * (1 - 2 * MARGIN);
    const maxHeight = window.innerHeight * (1 - 2 * MARGIN);

    // Calculate the required width and height based on config
    const requiredWidth =
        config.x_count * config.spacing * config.panel_count +
        config.spacing * (config.panel_count - 1);
    const requiredHeight = config.y_count * config.spacing;

    // Calculate scale factors for width and height
    const widthScale = maxWidth / requiredWidth;
    const heightScale = maxHeight / requiredHeight;

    // Use the smaller scale to ensure everything fits
    return Math.min(widthScale, heightScale, BASE_SCALE);
}

/**
 * Updates the canvas size based on current window dimensions
 */
function updateCanvasSize() {
    const scale = calculateScale();
    canvas.width = config.total_width * scale;
    canvas.height = config.total_height * scale;
}

/**
 * Draws a single LED at the specified position with the given color
 * @param {number} x - X coordinate
 * @param {number} y - Y coordinate
 * @param {{r: number, g: number, b: number, w?: number}} color - RGB color object
 * @param {number} scale - Scale factor
 * @param {Config} config - Configuration object
 */
function drawScale(x, y, color, scale, config) {
    // Calculate angle towards the center
    const centerX = config.total_width / 2;
    const centerY = config.total_height / 2 + config.scale_length / 2;

    // Calculate the angle from the LED position to the center
    const dx = centerX - x;
    const dy = centerY - y;
    const angle = Math.atan2(dy, dx);

    // Subtract 45 degrees (π/4 radians)
    const adjustedAngle = angle - Math.PI / 4;

    // Draw scale itself
    ctx.save();
    const offset =
        Math.sqrt((config.scale_length * config.scale_length) / 2) /
        Math.sqrt(2);
    // First translate to the LED center point
    ctx.translate(x * scale, y * scale);
    // Then rotate around this center point
    ctx.rotate(adjustedAngle);
    // Then translate by the offset to position the scale correctly
    ctx.translate(-offset, -offset);

    // Draw horizontal part of the scale
    ctx.beginPath();
    ctx.rect(0, 0, config.scale_length * scale, config.scale_width * scale);
    ctx.fillStyle = `#FFFFFF`;
    ctx.fill();

    // Draw vertical part of the scale
    ctx.beginPath();
    ctx.rect(0, 0, config.scale_width * scale, config.scale_length * scale);
    ctx.fillStyle = `#FFFFFF`;
    ctx.fill();

    ctx.restore();

    // Draw LED
    ctx.beginPath();
    ctx.arc(x * scale, y * scale, 5 * scale, 0, Math.PI * 2);
    ctx.fillStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
    ctx.fill();
}

/**
 * Updates all LEDs by fetching pixel data from the server and redrawing
 * @async
 * @returns {Promise<void>}
 */
async function updateLEDs() {
    try {
        /** @type {Array<Array<{red: number, green: number, blue: number, white: number}>>} */
        const pixelStrips = await fetch("/pixels").then((response) => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }
            return response.json();
        });

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const scale = calculateScale();
        for (let panel = 0; panel < config.panel_count; panel++) {
            let pixelIndex = 0;
            const panelOffsetX =
                panel * (config.x_count * config.spacing + config.spacing) +
                config.spacing / 2;

            // Process pixels in the same order, but map them to bottom-up coordinates
            for (let y = 0; y < config.y_count; y++) {
                // Calculate the actual y-coordinate (flipped vertically)
                const displayY =
                    config.total_height -
                    y * config.spacing -
                    config.spacing / 2;

                for (let x = 0; x < config.x_count - 1; x++) {
                    // Draw horizontal row
                    if (pixelIndex < pixelStrips[panel].length) {
                        drawScale(
                            panelOffsetX +
                                x * config.spacing +
                                config.spacing / 2,
                            displayY,
                            pixelStrips[panel][pixelIndex],
                            scale,
                            config
                        );
                        pixelIndex++;
                    }
                }
                for (let x = 0; x < config.x_count; x++) {
                    // Draw vertical row
                    if (pixelIndex < pixelStrips[panel].length) {
                        drawScale(
                            panelOffsetX + x * config.spacing,
                            displayY - config.spacing / 2,
                            pixelStrips[panel][pixelIndex],
                            scale,
                            config
                        );
                        pixelIndex++;
                    }
                }
            }
        }
    } catch (error) {
        console.error("Failed to update LEDs:", error);
        // Display error message on canvas
        ctx.font = "16px Arial";
        ctx.fillStyle = "red";
        ctx.fillText("Connection lost. Retrying...", 20, 50);
    }
}

/**
 * Initializes the visualizer by fetching configuration and setting up the canvas
 * @async
 * @returns {Promise<void>}
 */
async function initializeVisualizer() {
    try {
        // Get configuration from server
        config = await fetch("/config").then((response) => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }
            return response.json();
        });

        // Set initial canvas size
        updateCanvasSize();

        // Add resize handler
        window.addEventListener("resize", updateCanvasSize);

        // Start update loop
        function update() {
            updateLEDs();
            setTimeout(update, config.delay * 1000);
        }

        update();
    } catch (error) {
        console.error("Failed to initialize visualizer:", error);

        // Set a basic canvas size for error display
        canvas.width = window.innerWidth * 0.8;
        canvas.height = window.innerHeight * 0.8;

        // Display error message on canvas
        ctx.font = "16px Arial";
        ctx.fillStyle = "red";
        ctx.fillText(
            "Failed to connect to server. Retrying in 5 seconds...",
            20,
            50
        );

        // Retry initialization after 5 seconds
        setTimeout(initializeVisualizer, 5000);
    }
}

// Initialize the visualizer
initializeVisualizer();

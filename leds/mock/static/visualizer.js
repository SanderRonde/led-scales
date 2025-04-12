const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

/**
 * Configuration object loaded from server
 * @type {{x_count: number, y_count: number, panel_count: number, spacing: number}}
 */
let config = null;

/**
 * Initializes the visualizer by fetching configuration and setting up the canvas
 * @async
 * @returns {Promise<void>}
 */
async function initializeVisualizer() {
    // Get configuration from server
    config = await fetch('/config').then(response => response.json());
    
    // Calculate canvas size based on config
    const SCALE = 2; // Scale factor for better visibility
    canvas.width = (config.x_count * config.spacing * config.panel_count + config.spacing * (config.panel_count - 1)) * SCALE;
    canvas.height = (config.y_count + 0.5) * config.spacing * SCALE;
}

/**
 * Draws a single LED at the specified position with the given color
 * @param {number} x - X coordinate
 * @param {number} y - Y coordinate
 * @param {{red: number, green: number, blue: number, white?: number}} color - RGB color object
 */
function drawLED(x, y, color) {
    const SCALE = 2; // Match the scale factor used in canvas sizing
    ctx.beginPath();
    ctx.arc(x * SCALE, y * SCALE, 5 * SCALE, 0, Math.PI * 2);
    ctx.fillStyle = `rgb(${color.red}, ${color.green}, ${color.blue})`;
    ctx.fill();
}

/**
 * Updates all LEDs by fetching pixel data from the server and redrawing
 * @async
 * @returns {Promise<void>}
 */
async function updateLEDs() {
    if (!config) {
        await initializeVisualizer();
    }

    const pixels = await fetch('/pixels').then(response => response.json());
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    let pixelIndex = 0;
    for (let panel = 0; panel < config.panel_count; panel++) {
        const panelOffsetX = panel * (config.x_count * config.spacing + config.spacing);
        
        for (let y = 0; y < config.y_count; y++) {
            for (let x = 0; x < config.x_count; x++) {
                if (pixelIndex < pixels.length) {
                    drawLED(
                        panelOffsetX + x * config.spacing,
                        y * config.spacing,
                        pixels[pixelIndex]
                    );
                    pixelIndex++;
                }
            }
        }
    }
}

// Initialize and start update loop
initializeVisualizer().then(() => {
    // Update every 50ms
    setInterval(updateLEDs, 50);
}); 
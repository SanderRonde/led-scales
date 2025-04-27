const canvas = document.getElementById("canvas");
/** @type {CanvasRenderingContext2D} */
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

/** @type {WebSocket} */
let socket;

// UI Elements
const effectSelect = document.getElementById("effect-select");
const parametersDiv = document.getElementById("parameters");
const applyButton = document.getElementById("apply-effect");

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
function drawScale(index, x, y, color, scale, config) {
    // Calculate angle towards the center
    const centerX = config.total_width / 2;
    const centerY = config.total_height / 2 + config.scale_length / 2;

    //  // Draw the LED index as text
    // ctx.save();
    // ctx.font = `${10 * scale}px Arial`;
    // ctx.fillStyle = "#FFFFFF";
    // ctx.textAlign = "center";
    // ctx.textBaseline = "middle";
    // ctx.fillText(index.toString(), x * scale, y * scale);
    // ctx.restore();

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
 * Updates all LEDs by receiving pixel data from the WebSocket server and redrawing
 * @param {Array<Array<{r: number, g: number, b: number, w?: number}>>} pixelStrips - The pixel data received from the server
 */
function updateLEDsWithData(pixelStrips) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const scale = calculateScale();
    for (let panel = 0; panel < config.panel_count; panel++) {
        let pixelIndex = 0;
        const panelOffsetX =
            panel * (config.x_count * config.spacing + config.spacing) +
            config.spacing / 2;

        for (let x = 0; x < config.x_count; x++) {
            // Draw row from bottom to top
            for (let y = 0; y < config.y_count; y++) {
                if (pixelIndex < pixelStrips[panel].length) {
                    drawScale(
                        pixelIndex,
                        panelOffsetX + x * config.spacing,
                        config.total_height - (y + 1) * config.spacing,
                        pixelStrips[panel][pixelIndex],
                        scale,
                        config
                    );
                    pixelIndex++;
                }
            }

            // Then draw row from top to bottom
            if (x !== config.x_count - 1) {
                for (let y = config.y_count - 1; y >= 0; y--) {
                    if (pixelIndex < pixelStrips[panel].length) {
                        drawScale(
                            pixelIndex,
                            panelOffsetX +
                                x * config.spacing +
                                config.spacing / 2,
                            config.total_height -
                                y * config.spacing -
                                config.spacing / 2,
                            pixelStrips[panel][pixelIndex],
                            scale,
                            config
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

        // Initialize WebSocket connection
        socket = io();
        socket.on("connect", () => {
            console.log("Connected to WebSocket server");
        });
        socket.on("disconnect", () => {
            console.log("Disconnected from WebSocket server");
            // Display error message on canvas
            ctx.font = "16px Arial";
            ctx.fillStyle = "red";
            ctx.fillText("Connection lost. Retrying...", 20, 50);
        });
        socket.on("led_update", (data) => {
            updateLEDsWithData(data);
        });

        // Fetch available effects
        await fetchEffects();
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

/**
 * Resizes the canvas to fit its container
 */
function resizeCanvas() {
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();

/**
 * Fetches available effects from the server
 * @async
 * @returns {Promise<void>}
 */
async function fetchEffects() {
    try {
        const response = await fetch("/effects");
        const effects = await response.json();
        populateEffectSelect(effects);
    } catch (error) {
        console.error("Failed to fetch effects:", error);
    }
}

/**
 * Populates the effect dropdown with available effects
 * @param {Object} effects - Object containing effect definitions
 */
function populateEffectSelect(effects) {
    effectSelect.innerHTML = '<option value="">Select an effect...</option>';
    Object.keys(effects).forEach((effectName) => {
        const option = document.createElement("option");
        option.value = effectName;
        option.textContent = effectName;
        effectSelect.appendChild(option);
    });
}

/**
 * Creates parameter controls based on parameter types
 * @param {Object} parameters - Object containing parameter definitions
 */
function createParameterControls(parameters) {
    parametersDiv.innerHTML = "";

    Object.entries(parameters).forEach(([paramName, param]) => {
        const group = document.createElement("div");
        group.className = "parameter-group";

        const label = document.createElement("label");
        label.textContent = paramName;
        if (param.description) {
            label.title = param.description;
        }

        let input;
        switch (param.type) {
            case "float":
                input = createFloatInput(param, paramName);
                break;
            case "color":
                input = createColorInput(param, paramName);
                break;
            case "enum":
                input = createEnumInput(param, paramName);
                break;
            case "color_list":
                input = createColorListInput(param, paramName);
                break;
            default:
                console.warn(`Unknown parameter type: ${param.type}`);
                return;
        }

        group.appendChild(label);
        group.appendChild(input);
        parametersDiv.appendChild(group);
    });
}
/**
 * Creates a float input control
 * @param {Object} param - Parameter definition
 * @param {string} paramName - Name of the parameter
 * @returns {HTMLElement} The created input container
 */
function createFloatInput(param, paramName) {
    const container = document.createElement("div");
    container.className = "range-input";

    const input = document.createElement("input");
    input.type = "range";
    input.min = 0;
    input.max = 1;
    input.step = 0.05;
    input.value = param.value || param.default || 0;
    input.dataset.param = paramName;

    const valueDisplay = document.createElement("span");
    valueDisplay.textContent = input.value;

    input.addEventListener("input", () => {
        valueDisplay.textContent = input.value;
    });

    container.appendChild(input);
    container.appendChild(valueDisplay);
    return container;
}

/**
 * Creates a color input control
 * @param {Object} param - Parameter definition
 * @param {string} paramName - Name of the parameter
 * @returns {HTMLElement} The created input container
 */
function createColorInput(param, paramName) {
    const container = document.createElement("div");
    container.className = "color-input";

    const input = document.createElement("input");
    input.type = "color";
    input.value = rgbToHex(
        param.value || param.default || { r: 0, g: 0, b: 0 }
    );
    input.dataset.param = paramName;

    container.appendChild(input);
    return container;
}

/**
 * Creates an enum input control
 * @param {Object} param - Parameter definition
 * @param {string} paramName - Name of the parameter
 * @returns {HTMLElement} The created input container
 */
function createEnumInput(param, paramName) {
    const container = document.createElement("div");
    container.className = "enum-input";

    const select = document.createElement("select");
    select.dataset.param = paramName;

    param.enum_values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        if (value === (param.value || param.default)) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    container.appendChild(select);
    return container;
}

/**
 * Creates a color list input control
 * @param {Object} param - Parameter definition
 * @param {string} paramName - Name of the parameter
 * @returns {HTMLElement} The created input container
 */
function createColorListInput(param, paramName) {
    const container = document.createElement("div");
    container.className = "color-list-input";

    const colors = param.value || param.default || [];
    colors.forEach((color, index) => {
        const colorContainer = document.createElement("div");
        colorContainer.className = "color-item";

        const input = document.createElement("input");
        input.type = "color";
        input.value = rgbToHex(color);
        input.dataset.param = `${paramName}[${index}]`;

        const removeBtn = document.createElement("button");
        removeBtn.textContent = "×";
        removeBtn.onclick = () => colorContainer.remove();

        colorContainer.appendChild(input);
        colorContainer.appendChild(removeBtn);
        container.appendChild(colorContainer);
    });

    const addBtn = document.createElement("button");
    addBtn.textContent = "Add Color";
    addBtn.onclick = () => {
        const colorContainer = document.createElement("div");
        colorContainer.className = "color-item";

        const input = document.createElement("input");
        input.type = "color";
        input.value = "#000000";
        const currentColorCount =
            container.querySelectorAll(".color-item").length;
        input.dataset.param = `${paramName}[${currentColorCount}]`;

        const removeBtn = document.createElement("button");
        removeBtn.textContent = "×";
        removeBtn.onclick = () => colorContainer.remove();

        colorContainer.appendChild(input);
        colorContainer.appendChild(removeBtn);
        container.appendChild(colorContainer);
    };

    container.appendChild(addBtn);
    return container;
}

/**
 * Converts an RGB color object to a hex string
 * @param {{r: number, g: number, b: number}} color - RGB color object
 * @returns {string} Hex color string
 */
function rgbToHex(color) {
    return `#${color.r.toString(16).padStart(2, "0")}${color.g
        .toString(16)
        .padStart(2, "0")}${color.b.toString(16).padStart(2, "0")}`;
}

/**
 * Converts a hex color string to an RGB object
 * @param {string} hex - Hex color string
 * @returns {{r: number, g: number, b: number}|null} RGB color object or null if invalid
 */
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
        ? {
              r: parseInt(result[1], 16),
              g: parseInt(result[2], 16),
              b: parseInt(result[3], 16),
          }
        : null;
}

// Handle effect selection
effectSelect.addEventListener("change", async () => {
    const effectName = effectSelect.value;
    if (!effectName) return;

    try {
        const response = await fetch("/effects");
        const effects = await response.json();
        const effect = effects[effectName];
        if (effect) {
            createParameterControls(effect);
        }
    } catch (error) {
        console.error("Failed to fetch effect details:", error);
    }
});

// Apply selected effect
applyButton.addEventListener("click", async () => {
    const effectName = effectSelect.value;
    if (!effectName) return;

    const parameters = {};
    document
        .querySelectorAll("#parameters input, #parameters select")
        .forEach((input) => {
            const paramName = input.dataset.param;
            if (!paramName) return;

            if (paramName.includes("[")) {
                // Handle color list
                const [baseName, indexStr] = paramName.split("[");
                const index = parseInt(indexStr);
                if (!parameters[baseName]) {
                    parameters[baseName] = [];
                }
                parameters[baseName][index] = hexToRgb(input.value);
            } else {
                // Handle other parameters
                if (input.type === "color") {
                    parameters[paramName] = hexToRgb(input.value);
                } else if (input.type === "range") {
                    parameters[paramName] = parseFloat(input.value);
                } else {
                    parameters[paramName] = input.value;
                }
            }
        });

    try {
        const response = await fetch("/effects", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                effect_name: effectName,
                parameters: parameters,
            }),
        });

        if (!response.ok) {
            throw new Error(
                `Server returned ${response.status}: ${response.statusText}`
            );
        }

        console.log("Effect applied successfully");
    } catch (error) {
        console.error("Failed to apply effect:", error);
    }
});

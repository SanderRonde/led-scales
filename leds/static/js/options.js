// UI Elements
const effectSelect = document.getElementById("effect-select");
const parametersDiv = document.getElementById("parameters");
const applyButton = document.getElementById("apply-effect");
const powerButton = document.getElementById("power-button");
const brightnessSlider = document.getElementById("brightness-slider");
const brightnessValue = brightnessSlider.nextElementSibling;

/**
 * @typedef {Object} Effects
 * @property {string} current_effect - The name of the current effect
 * @property {Record<string, string>} effect_names - The names of all available effects
 * @property {Record<string, Record<string, any>>} effect_parameters - The parameters of the current effect
 */

/**
 * Fetches available effects from the server
 * @async
 * @returns {Promise<void>}
 */
export async function fetchEffects() {
    try {
        const response = await fetch("/effects");
        /** @type {Effects} */
        const effects = await response.json();
        const {
            effect_parameters: effectParameters,
            effect_names: effectNames,
            current_effect: currentEffect,
        } = effects;
        populateEffectSelect(effectParameters, effectNames);
        effectSelect.value = currentEffect;
        await onEffectChange(currentEffect);
    } catch (error) {
        console.error("Failed to fetch effects:", error);
    }
}

/**
 * Populates the effect dropdown with available effects
 * @param {Object} effects - Object containing effect definitions
 */
function populateEffectSelect(effectParameters, effectNames) {
    effectSelect.innerHTML = '<option value="">Select an effect...</option>';
    Object.keys(effectNames).forEach((effectName) => {
        const option = document.createElement("option");
        option.value = effectName;
        option.textContent = effectNames[effectName];
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

/**
 * @param {string} effectName
 */
async function onEffectChange(effectName) {
    try {
        const response = await fetch("/effects");
        /** @type {Effects} */
        const effects = await response.json();
        const {
            effect_parameters: effectParameters,
            current_effect: currentEffect,
        } = effects;
        const effect = effectParameters[effectName];
        if (effect) {
            createParameterControls(effect);
        }
    } catch (error) {
        console.error("Failed to fetch effect details:", error);
    }
}

// Handle effect selection
effectSelect.addEventListener("change", async () => {
    if (effectSelect.value) {
        await onEffectChange(effectSelect.value);
    }
});

// Apply selected effect
applyButton.addEventListener("click", async () => {
    await applyEffect();
});

export async function applyEffect() {
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
                if (!parameters[baseName]) {
                    parameters[baseName] = [];
                }
                parameters[baseName].push(hexToRgb(input.value));
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
}

/**
 * Initializes the brightness slider and power button
 */
async function initializeControls() {
    try {
        const response = await fetch("/state");
        const { brightness, power_state } = await response.json();

        updateBrightnessSliderState(brightness);

        // Initialize power button
        updatePowerButtonState(power_state);
    } catch (error) {
        console.error("Failed to fetch state:", error);
    }

    // Brightness slider event listeners
    brightnessSlider.addEventListener("input", () => {
        brightnessValue.textContent = `${brightnessSlider.value}%`;
    });

    brightnessSlider.addEventListener("change", async () => {
        try {
            await fetch("/state", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    brightness: parseInt(brightnessSlider.value) / 100,
                }),
            });
        } catch (error) {
            console.error("Failed to set brightness:", error);
        }
    });

    // Power button event listener
    powerButton.addEventListener("click", async () => {
        const currentState = !powerButton.classList.contains("off");
        try {
            await fetch("/state", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ power_state: !currentState }),
            });
            updatePowerButtonState(!currentState);
        } catch (error) {
            console.error("Failed to toggle power:", error);
        }
    });
}

export function updateBrightnessSliderState(brightness) {
    // Initialize brightness slider
    brightnessSlider.value = Math.round(brightness * 100);
    brightnessValue.textContent = `${brightnessSlider.value}%`;
}

// Initialize controls when the page loads
initializeControls();

/**
 * Updates the power button state and appearance
 * @param {boolean} isOn - Whether the power is on
 */
function updatePowerButtonState(isOn) {
    powerButton.textContent = isOn ? "Power Off" : "Power On";
    powerButton.classList.toggle("off", !isOn);
}

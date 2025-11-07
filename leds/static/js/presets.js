import {
    applyEffect,
    getParameters,
    updateBrightnessSliderState,
} from "./options.js";

/**
 * @typedef {Object} Preset
 * @property {number} id - Unique identifier for the preset
 * @property {string} name - Name of the preset
 * @property {string} effect - The effect name
 * @property {number} brightness - Brightness value between 0 and 1
 * @property {Object} parameters - Effect parameters
 */

/**
 * Manages LED presets including saving, loading, and applying
 * @class
 */
class PresetManager {
    /**
     * Creates a new PresetManager instance
     * @constructor
     */
    constructor() {
        this.presets = [];
        this.currentPreset = null;
        this.presetList = document.getElementById("preset-list");
        this.saveButton = document.getElementById("save-preset");
        this.presetNameInput = document.getElementById("preset-name");

        this.initializeEventListeners();
        this.loadPresets();
    }

    async loadPresets() {
        try {
            const response = await fetch("/presets");
            if (response.ok) {
                this.presets = await response.json();
                this.renderPresets();
            }
        } catch (error) {
            console.error("Error loading presets:", error);
        }
    }

    /**
     * Sets up event listeners for preset management
     * @private
     */
    initializeEventListeners() {
        this.saveButton.addEventListener("click", () =>
            this.saveCurrentPreset()
        );
        this.presetNameInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                this.saveCurrentPreset();
            }
        });
    }

    /**
     * Saves the current LED configuration as a preset
     * @private
     */
    async saveCurrentPreset() {
        const name = this.presetNameInput.value.trim();
        if (!name) return;

        const preset = {
            name,
            effect: document.getElementById("effect-select").value,
            brightness:
                parseInt(document.getElementById("brightness-slider").value) /
                100,
            parameters: this.getCurrentParameters(),
        };

        try {
            const response = await fetch("/presets", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(preset),
            });

            if (response.ok) {
                const savedPreset = await response.json();
                await this.loadPresets(); // Reload all presets
                this.presetNameInput.value = "";
            }
        } catch (error) {
            console.error("Error saving preset:", error);
        }
    }

    /**
     * Gets the current parameter values from the UI
     * @private
     * @returns {Object} Parameter values keyed by input ID
     */
    getCurrentParameters() {
        return getParameters();
    }

    /**
     * Applies a preset to the LED system
     * @param {Preset} preset - The preset to apply
     * @returns {Promise<void>}
     */
    async applyPreset(preset) {
        try {
            // Update UI elements
            document.getElementById("effect-select").value = preset.effect;
            updateBrightnessSliderState(preset.brightness);

            // Trigger effect change to update parameters
            const event = new Event("change");
            document.getElementById("effect-select").dispatchEvent(event);

            // Set parameters after a short delay to allow parameter inputs to be created
            setTimeout(() => {
                Object.entries(preset.parameters).forEach(([id, value]) => {
                    const input = document.getElementById(id);
                    if (input) {
                        input.value = value;
                        input.dispatchEvent(new Event("change"));
                    }
                });
            }, 100);

            // Apply the preset on the server
            const response = await fetch("/presets/apply", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(preset),
            });

            if (response.ok) {
                this.currentPreset = preset;
                this.renderPresets();
            }
        } catch (error) {
            console.error("Error applying preset:", error);
        }
    }

    /**
     * Deletes a preset by ID
     * @param {number} presetId - ID of the preset to delete
     */
    async deletePreset(presetId) {
        try {
            const response = await fetch(`/presets/${presetId}`, {
                method: "DELETE",
            });

            if (response.ok) {
                await this.loadPresets(); // Reload all presets
            }
        } catch (error) {
            console.error("Error deleting preset:", error);
        }
    }

    /**
     * Renders the preset list in the UI
     * @private
     */
    renderPresets() {
        this.presetList.innerHTML = "";

        this.presets.forEach((preset) => {
            const presetElement = document.createElement("div");
            presetElement.className = `preset-item ${
                this.currentPreset?.id === preset.id ? "active" : ""
            }`;
            presetElement.innerHTML = `
                <span>${preset.name}</span>
                <div class="preset-actions">
                    <button class="delete" data-id="${preset.id}">Delete</button>
                </div>
            `;

            presetElement.addEventListener("click", () =>
                this.applyPreset(preset)
            );

            const deleteButton = presetElement.querySelector(".delete");
            deleteButton.addEventListener("click", (e) => {
                e.stopPropagation();
                this.deletePreset(preset.id);
            });

            this.presetList.appendChild(presetElement);
        });
    }
}

// Initialize the preset manager when the DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
    window.presetManager = new PresetManager();
});

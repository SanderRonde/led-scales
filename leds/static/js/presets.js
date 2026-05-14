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
        /** @type {number|null} */
        this.defaultPresetId = null;
        this.presetList = document.getElementById("preset-list");
        this.saveButton = document.getElementById("save-preset");
        this.presetNameInput = document.getElementById("preset-name");

        document.addEventListener("led-state-update", (e) => {
            const ev = /** @type {CustomEvent} */ (e);
            this.onServerState(ev.detail);
        });
        document.addEventListener("led-presets-update", (e) => {
            const ev = /** @type {CustomEvent} */ (e);
            const presets = ev.detail;
            if (Array.isArray(presets)) {
                this.presets = presets;
                this.renderPresets();
            }
        });

        this.initializeEventListeners();
        this.initialLoad();
    }

    /**
     * @param {{ active_preset_id?: number|null, default_preset_id?: number|null }} data
     */
    onServerState(data) {
        if (data.default_preset_id !== undefined) {
            this.defaultPresetId = data.default_preset_id;
        }
        const aid = data.active_preset_id;
        if (aid != null) {
            this.currentPreset =
                this.presets.find((p) => p.id === aid) ?? null;
        } else {
            this.currentPreset = null;
        }
        this.renderPresets();
    }

    async initialLoad() {
        await this.loadPresets();
        await this.syncStateFromServer();
    }

    async syncStateFromServer() {
        try {
            const response = await fetch("/state");
            if (response.ok) {
                const data = await response.json();
                this.onServerState(data);
            }
        } catch (error) {
            console.error("Error loading state for presets:", error);
        }
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
                await this.syncStateFromServer();
            }
        } catch (error) {
            console.error("Error applying preset:", error);
        }
    }

    /**
     * Set or clear which preset loads when the server starts.
     * @param {Preset} preset
     */
    async toggleStartupDefault(preset) {
        const isDefault = this.defaultPresetId === preset.id;
        const id = isDefault ? null : preset.id;
        try {
            const response = await fetch("/presets/default", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id }),
            });
            if (response.ok) {
                const data = await response.json();
                this.defaultPresetId = data.default_preset_id ?? null;
                this.renderPresets();
            }
        } catch (error) {
            console.error("Error setting startup preset:", error);
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
                await this.loadPresets();
                await this.syncStateFromServer();
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
            const isActive = this.currentPreset?.id === preset.id;
            const isStartupDefault = this.defaultPresetId === preset.id;

            const presetElement = document.createElement("div");
            presetElement.className = [
                "preset-item",
                isActive ? "active" : "",
                isStartupDefault ? "startup-default" : "",
            ]
                .filter(Boolean)
                .join(" ");

            presetElement.innerHTML = `
                <div class="preset-main">
                    <span class="preset-name">${preset.name}</span>
                    ${
                        isStartupDefault
                            ? '<span class="preset-startup-badge" title="This preset runs when the server starts">On startup</span>'
                            : ""
                    }
                </div>
                <div class="preset-actions">
                    <button type="button" class="startup-default-btn ${
                        isStartupDefault ? "is-on" : ""
                    }" data-id="${preset.id}" title="${
                isStartupDefault
                    ? "Clear startup preset"
                    : "Use this preset when the server starts"
            }">★</button>
                    <button type="button" class="delete" data-id="${preset.id}">Delete</button>
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

            const startupBtn = presetElement.querySelector(".startup-default-btn");
            startupBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                this.toggleStartupDefault(preset);
            });

            this.presetList.appendChild(presetElement);
        });
    }
}

// Initialize the preset manager when the DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
    window.presetManager = new PresetManager();
});

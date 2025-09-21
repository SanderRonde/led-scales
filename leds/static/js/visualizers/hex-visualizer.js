import { LEDVisualizerBase } from "./visualizer-base.js";

/**
 * @typedef {Object} Hexagon
 * @property {number} x - X coordinate
 * @property {number} y - Y coordinate
 * @property {number[]} ordered_leds - Array of LED indices
 * @property {number[]} setup_mode_leds - Array of LED indices for setup mode
 */

/**
 * @typedef {Object} HexConfig
 * @property {'hex'} type - Type of visualizer
 * @property {number} hex_size - Size of each hexagon
 * @property {Hexagon[]} hexagons - Array of hexagons
 * @property {number} max_x - Maximum x coordinate
 * @property {number} max_y - Maximum y coordinate
 * @property {boolean} setup_mode - Whether we're in setup mode
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

        this.currentLedIndex = 0;
    }

    /**
     * Draws a simple hexagon at the specified position
     * @param {number} x - X coordinate of center
     * @param {number} y - Y coordinate of center
     * @param {number} hexIndex - Index of the hexagon
     * @param {import("./visualizer-base.js").LED[][]} pixelStrips - The pixel data received from the server
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

        // Draw hexagon outline
        this.ctx.closePath();
        this.ctx.lineWidth = 1;
        this.ctx.strokeStyle = `rgb(255, 255, 255)`;
        this.ctx.stroke();

        const hexagon = this.config.hexagons[hexIndex];
        if (this.config.setup_mode) {
            // In setup mode, show hexagon number and assigned LEDs count
            this.ctx.fillStyle = "white";
            this.ctx.font = `${12 * scale}px Arial`;
            this.ctx.textAlign = "center";
            this.ctx.textBaseline = "middle";

            this.ctx.fillText(`H${hexIndex}`, x, y - 10 * scale);
            this.ctx.fillText(
                `(${hexagon.setup_mode_leds.length})`,
                x,
                y + 10 * scale
            );

            // Highlight if this hexagon has LEDs assigned
            if (hexagon.setup_mode_leds.length > 0) {
                this.ctx.beginPath();
                this.ctx.arc(
                    x,
                    y,
                    (this.config.hex_size / 2) * scale * 0.9,
                    0,
                    Math.PI * 2
                );
                this.ctx.fillStyle = "rgba(0, 255, 0, 0.2)";
                this.ctx.fill();
            }
        } else {
            // Normal mode - draw LEDs
            const ledList = this.config.hexagons[hexIndex].ordered_leds;
            for (let i = 0; i < ledList.length; i++) {
                const angle = (i * Math.PI * 2) / ledList.length;
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
                const ledIndex = ledList[i];
                if (pixelStrips[0] && pixelStrips[0][ledIndex]) {
                    // Apply brightness to RGB values
                    const brightness =
                        pixelStrips[0][ledIndex].brightness / 255;
                    this.ctx.fillStyle = `rgb(${
                        pixelStrips[0][ledIndex].r * brightness
                    }, ${pixelStrips[0][ledIndex].g * brightness}, ${
                        pixelStrips[0][ledIndex].b * brightness
                    })`;
                } else {
                    this.ctx.fillStyle = "rgb(50, 50, 50)";
                }
                this.ctx.fill();
            }
        }
        this.ctx.restore();
    }

    /**
     * Updates all LEDs by receiving pixel data from the WebSocket server and redrawing
     * @param {import("./visualizer-base.js").LED[][]} pixelStrips - The pixel data received from the server
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

    /**
     * Initialize setup mode if needed
     */
    async initialize() {
        await super.initialize();

        if (this.config.setup_mode) {
            this.initializeSetupMode();
        }
    }

    /**
     * Initialize setup mode UI and event handlers
     */
    initializeSetupMode() {
        // Create setup UI
        this.createSetupUI();

        // Sync current LED index with server periodically
        this.syncCurrentLed();
        setInterval(() => this.syncCurrentLed(), 1000);
    }

    /**
     * Sync current LED index with server
     */
    async syncCurrentLed() {
        try {
            const response = await fetch("/setup/current-led");
            if (response.ok) {
                const result = await response.json();
                this.currentLedIndex = result.current_led;
                this.updateSetupUI();
            }
        } catch (error) {
            console.error("Error syncing current LED:", error);
        }
    }


    /**
     * Assign the current LED to a hexagon
     */
    async assignCurrentLedToHex(hexIndex) {
        try {
            const assignResponse = await fetch("/setup/hex/assign", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    hex_index: hexIndex,
                    led_index: this.currentLedIndex,
                }),
            });

            if (!assignResponse.ok) {
                console.error("Failed to assign LED:", await response.text());
                return;
            }

            const assignResult = await assignResponse.json();
            console.log(
                `Assigned LED ${assignResult.led_index} to hexagon ${assignResult.hex_index}`
            );

            const nextResponse = await fetch("/setup/next", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({}),
            });

            if (!nextResponse.ok) {
                console.error(
                    "Failed to get next LED:",
                    await nextResponse.text()
                );
                return;
            }

            const nextResult = await nextResponse.json();
            this.currentLedIndex = nextResult.current_led;

            // Update config
            const config = await fetch("/config").then((response) => {
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}`);
                }
                return response.json();
            });

            this.config = config;
            this.updateSetupUI();
        } catch (error) {
            console.error("Error assigning LED:", error);
        }
    }

    /**
     * Create the setup mode UI
     */
    createSetupUI() {
        // Replace the normal control panel with setup UI
        const controlPanel = document.querySelector(".control-panel");
        if (!controlPanel) return;

        controlPanel.innerHTML = `
            <h2>LED Setup Mode</h2>
            <div class="setup-info">
                <p>Current LED: <span id="current-led">${this.currentLedIndex}</span></p>
                <p>Click a hex button below to assign the current LED to it.</p>
            </div>
            <div class="hex-buttons" id="hex-buttons">
                ${this.createHexButtons()}
            </div>
            <div class="setup-controls">
                <button id="reset-setup">Reset All</button>
                <button id="export-config">Export Config</button>
            </div>
            <div id="export-output" style="display: none;">
                <h3>Configuration Code:</h3>
                <textarea id="config-code" readonly style="width: 100%; height: 200px; font-family: monospace;"></textarea>
                <button id="copy-config">Copy to Clipboard</button>
            </div>
        `;

        // Add event listeners
        document.getElementById("reset-setup").addEventListener("click", () => {
            this.resetSetup();
        });

        document
            .getElementById("export-config")
            .addEventListener("click", () => {
                this.exportConfig();
            });

        document.getElementById("copy-config").addEventListener("click", () => {
            this.copyConfigToClipboard();
        });

        // Add hex button event listeners
        this.addHexButtonListeners();
    }

    /**
     * Create hex buttons HTML
     */
    createHexButtons() {
        let buttonsHTML = '';
        for (let i = 0; i < this.config.hexagons.length; i++) {
            const hexagon = this.config.hexagons[i];
            const ledCount = hexagon.setup_mode_leds ? hexagon.setup_mode_leds.length : 0;
            buttonsHTML += `
                <button class="hex-button" data-hex-index="${i}" style="margin: 2px; padding: 8px; min-width: 60px; background: ${ledCount > 0 ? '#4CAF50' : '#666'};">
                    H${i} (${ledCount})
                </button>
            `;
        }
        return buttonsHTML;
    }

    /**
     * Add event listeners to hex buttons
     */
    addHexButtonListeners() {
        const hexButtons = document.querySelectorAll('.hex-button');
        hexButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                const hexIndex = parseInt(event.target.getAttribute('data-hex-index'));
                this.assignCurrentLedToHex(hexIndex);
            });
        });
    }

    /**
     * Update the setup UI
     */
    updateSetupUI() {
        const currentLedElement = document.getElementById("current-led");
        if (currentLedElement) {
            currentLedElement.textContent = this.currentLedIndex;
        }

        // Update hex buttons
        const hexButtonsContainer = document.getElementById("hex-buttons");
        if (hexButtonsContainer) {
            hexButtonsContainer.innerHTML = this.createHexButtons();
            this.addHexButtonListeners();
        }
    }

    /**
     * Reset all LED assignments
     */
    async resetSetup() {
        try {
            const response = await fetch("/setup/hex/reset", {
                method: "POST",
            });

            if (response.ok) {
                this.currentLedIndex = 0;
                this.setupAssignments.clear();
                this.config.hexagons.forEach((hex, index) => {
                    this.setupAssignments.set(index, []);
                });
                this.updateSetupUI();
                console.log("Setup reset successfully");
            } else {
                console.error("Failed to reset setup:", await response.text());
            }
        } catch (error) {
            console.error("Error resetting setup:", error);
        }
    }

    /**
     * Export the current configuration
     */
    async exportConfig() {
        try {
            const response = await fetch("/setup/hex/export");
            if (response.ok) {
                const result = await response.json();
                const exportOutput = document.getElementById("export-output");
                const configCode = document.getElementById("config-code");

                if (exportOutput && configCode) {
                    configCode.value = result.config_code;
                    exportOutput.style.display = "block";
                }
            } else {
                console.error(
                    "Failed to export config:",
                    await response.text()
                );
            }
        } catch (error) {
            console.error("Error exporting config:", error);
        }
    }

    /**
     * Copy configuration to clipboard
     */
    async copyConfigToClipboard() {
        const configCode = document.getElementById("config-code");
        if (configCode) {
            try {
                await navigator.clipboard.writeText(configCode.value);
                alert("Configuration copied to clipboard!");
            } catch (error) {
                console.error("Failed to copy to clipboard:", error);
                // Fallback: select the text
                configCode.select();
                configCode.setSelectionRange(0, 99999);
            }
        }
    }

    /**
     * Get the current scale factor
     */
    getScale() {
        const dimensions = this.getDimensions();
        const scaleX = this.canvas.width / dimensions.width;
        const scaleY = this.canvas.height / dimensions.height;
        return Math.min(scaleX, scaleY);
    }
}

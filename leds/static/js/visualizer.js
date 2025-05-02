import { ScaleLEDVisualizer } from "./visualizers/scale-visualizer.js";
import { HexLEDVisualizer } from "./visualizers/hex-visualizer.js";
/**
 * Initializes the visualizer by fetching configuration and setting up the canvas
 * @async
 * @returns {Promise<void>}
 */
export async function initializeVisualizer() {
    // Get configuration from server
    const config = await fetch("/config").then((response) => {
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }
        return response.json();
    });

    let visualizer;
    if (config.type === "scale") {
        visualizer = new ScaleLEDVisualizer(config);
    } else if (config.type === "hex") {
        visualizer = new HexLEDVisualizer(config);
    } else {
        throw new Error(`Unknown visualizer type: ${config.type}`);
    }
    await visualizer.initialize();
}

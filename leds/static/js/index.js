import { initializeVisualizer } from "./visualizer.js";
import { fetchEffects } from "./options.js";
import './presets.js';

async function main() {
    await initializeVisualizer();
    await fetchEffects();
}

main();

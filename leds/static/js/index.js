import { initializeVisualizer } from "./visualizer.js";
import { fetchEffects } from "./options.js";

async function main() {
    await initializeVisualizer();
    await fetchEffects();
}

main();

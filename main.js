// main.js
// Entry point: orchestrates data loading, UI, chart, and controls
import { loadData } from './dataLoader.js';
import { initChart, updateChart } from './chartHandler.js';
import { populateUI, updateUICheckboxes, setupModeButtons, setupSmoothButton } from './uiHandler.js';
import { setupUserControls } from './userControls.js';

async function main() {
    // Wait for fonts to load before rendering
    if (document.fonts && document.fonts.ready) {
        await document.fonts.ready;
    }
    const { config, data } = await loadData();
    // Example symbolState initialization
    const symbolState = {};
    const allSymbols = (config.symbols || []).map(item => item.field_name).filter(s => s !== 'events');
    let colorIdx = 0;
    allSymbols.forEach(sym => {
        symbolState[sym] = { selected: false, colorIdx: colorIdx++ };
    });
    // Select the first available symbol by default
    const firstAvailable = allSymbols.find(sym => data[sym]);
    if (firstAvailable) symbolState[firstAvailable].selected = true;

    // Example options
    let options = {
        selectedSymbols: Object.keys(symbolState).filter(sym => symbolState[sym].selected),
        normalized: false,
        indexed: false
    };

    // Debug logs for symbol categorization and state
    // Debug logs removed

    // Initialize chart
    const chartContainer = document.getElementById('casinoChart');
    let chart = initChart(chartContainer, config, data, symbolState, options);

    // Populate UI and connect symbol selection to chart update
    populateUI(config, data, symbolState, (sym, checked) => {
        options.selectedSymbols = Object.keys(symbolState).filter(s => symbolState[s].selected);
        updateChart(chart, config, data, symbolState, options);
        updateUICheckboxes(symbolState);
    });

    // Initial checkbox UI sync
    updateUICheckboxes(symbolState);

    // Initialize user controls (scroll, modal, sidebar, etc.)
    setupUserControls(chart);

    // --- Mode and Smooth Button Logic ---
    setupModeButtons(options, chart, config, data, symbolState, updateChart);
    setupSmoothButton(chart, config, data, symbolState, options, updateChart);
}

if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', main);
} else {
    main();
}

// uiHandler.js
// Handles UI population and updates (checkboxes, buttons, etc.)
import { getColor } from './chartHandler.js';

// Helper to build symbolNames and symbolCategories from config
export function categorizeSymbols(config) {
    const symbolNames = {};
    const symbolCategories = {};
    (config.symbols || []).forEach(item => {
        symbolNames[item.field_name] = item.desc;
        const cat = item.category || 'Other';
        if (!symbolCategories[cat]) symbolCategories[cat] = [];
        symbolCategories[cat].push(item.field_name);
    });
    return { symbolNames, symbolCategories };
}

export function populateUI(config, data, symbolState, onSymbolChange) {
    const { symbolNames, symbolCategories } = categorizeSymbols(config);
    const seriesCategories = document.getElementById('series-categories');
    seriesCategories.innerHTML = '';
    const catCheckboxes = {};
    const categoryToCheckboxes = {};
    Object.keys(symbolCategories).forEach(cat => {
        const syms = symbolCategories[cat] || [];
        if (syms.length === 0) return;
        // Category label as direct child
        const labelDiv = document.createElement('div');
        labelDiv.className = 'category-label';
        const catCheckbox = document.createElement('input');
        catCheckbox.type = 'checkbox';
        catCheckbox.className = 'category-checkbox';
        catCheckbox.setAttribute('data-category', cat);
        labelDiv.appendChild(catCheckbox);
        labelDiv.appendChild(document.createTextNode(cat.toUpperCase()));
        catCheckboxes[cat] = catCheckbox;
        labelDiv.addEventListener('click', function(e) {
            if (e.target !== catCheckbox) {
                const cbs = categoryToCheckboxes[cat].filter(cb => !cb.disabled);
                const allChecked = cbs.length > 0 && cbs.every(cb => cb.checked);
                cbs.forEach(cb => { cb.checked = !allChecked; cb.dispatchEvent(new Event('change', {bubbles:true})); });
            }
        });
        seriesCategories.appendChild(labelDiv);
        // Series checkboxes as direct children
        categoryToCheckboxes[cat] = [];
        syms.forEach(sym => {
            const itemLabel = document.createElement('label');
            itemLabel.setAttribute('data-symbol', sym);
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = sym;
            cb.checked = symbolState[sym] && symbolState[sym].selected;
            if (!data[sym] || (Array.isArray(data[sym]) && data[sym].length === 0)) {
                cb.disabled = true;
                itemLabel.classList.add('disabled');
            }
            itemLabel.appendChild(cb);
            itemLabel.appendChild(document.createTextNode(' ' + (symbolNames[sym] || sym)));
            itemLabel.title = sym;
            seriesCategories.appendChild(itemLabel);
            categoryToCheckboxes[cat].push(cb);
            itemLabel.addEventListener('click', function(e) {
                if (e.target === cb) return;
                e.preventDefault();
                if (!cb.disabled) {
                    cb.checked = !cb.checked;
                    cb.dispatchEvent(new Event('change', {bubbles:true}));
                }
            });
            cb.addEventListener('change', function() {
                if (symbolState[sym]) symbolState[sym].selected = cb.checked;
                // Update category checkbox state
                const catCheckbox = catCheckboxes[cat];
                const cbs = categoryToCheckboxes[cat].filter(cb2 => !cb2.disabled);
                const checkedCount = cbs.filter(cb2 => cb2.checked).length;
                if (cbs.length > 0 && checkedCount === cbs.length) {
                    catCheckbox.checked = true;
                    catCheckbox.indeterminate = false;
                } else if (checkedCount === 0) {
                    catCheckbox.checked = false;
                    catCheckbox.indeterminate = false;
                } else {
                    catCheckbox.checked = false;
                    catCheckbox.indeterminate = true;
                }
                if (typeof onSymbolChange === 'function') onSymbolChange(sym, cb.checked);
            });
        });
        // Add separator after last item in category
        const separator = document.createElement('div');
        separator.className = 'category-placeholder';
        seriesCategories.appendChild(separator);
        catCheckbox.addEventListener('change', function(e) {
            const cbs = categoryToCheckboxes[cat];
            cbs.forEach(cb => { cb.checked = catCheckbox.checked; cb.dispatchEvent(new Event('change', {bubbles:true})); });
        });
    });
}

export function updateUICheckboxes(symbolState) {
    Object.keys(symbolState).forEach(sym => {
        const label = document.querySelector('label[data-symbol="' + sym + '"]');
        if (!label) return;
        if (symbolState[sym].selected) {
            label.classList.add('active');
            // Set background to series color
            const colorIdx = symbolState[sym].colorIdx || 0;
            label.style.background = getColor(colorIdx);
            label.style.color = '#000';
        } else {
            label.classList.remove('active');
            label.style.background = '';
            label.style.color = '';
        }
    });
}

export function setupModeButtons(options, chart, config, data, symbolState, updateChart) {
    const modeBtns = Array.from(document.querySelectorAll('.mode-btn[data-mode]'));
    function setModeActive(mode) {
        modeBtns.forEach(btn => {
            if (btn.dataset.mode === mode) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }
    // Set initial mode button active (raw by default)
    setModeActive(options.normalized ? 'normalized' : options.indexed ? 'indexed' : 'raw');
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            options.normalized = (mode === 'normalized');
            options.indexed = (mode === 'indexed');
            setModeActive(mode);
            updateChart(chart, config, data, symbolState, options);
        });
    });
}

export function setupSmoothButton(chart, config, data, symbolState, options, updateChart) {
    const smoothBtn = document.getElementById('smooth-btn');
    if (smoothBtn) {
        if (typeof window.smoothLineEnabled === 'undefined') {
            window.smoothLineEnabled = false;
        }
        // Set initial button state
        if (window.smoothLineEnabled) {
            smoothBtn.classList.add('active');
        } else {
            smoothBtn.classList.remove('active');
        }
        smoothBtn.addEventListener('click', () => {
            window.smoothLineEnabled = !window.smoothLineEnabled;
            if (window.smoothLineEnabled) {
                smoothBtn.classList.add('active');
            } else {
                smoothBtn.classList.remove('active');
            }
            updateChart(chart, config, data, symbolState, options);
        });
    }
}

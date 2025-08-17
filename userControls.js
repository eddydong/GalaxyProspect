// userControls.js
// Handles user controls (scroll, window, modals, etc.)

// Disable all default scroll, selection, and drag for the whole page
function preventDefaultScrolls() {
    document.addEventListener('wheel', function(e) { e.preventDefault(); }, { passive: false });
    document.addEventListener('selectstart', function(e) { e.preventDefault(); });
    document.addEventListener('dragstart', function(e) { e.preventDefault(); });
    document.addEventListener('touchmove', function(e) { e.preventDefault(); }, { passive: false });
    // Also block horizontal scroll globally to prevent browser navigation
    document.addEventListener('wheel', function(e) {
        if (Math.abs(e.deltaX) > 0) e.preventDefault();
    }, { passive: false });
}

// About modal show/hide logic
function setupAboutModal() {
    const modal = document.getElementById('about-modal');
    if (!modal) return;
    function showAbout() {
        modal.classList.add('visible');
    }
    modal.addEventListener('click', function() {
        this.classList.remove('visible');
    });
    const helpBtn = document.getElementById('help-btn');
    if (helpBtn) {
        helpBtn.addEventListener('click', function(e) {
            showAbout();
            e.stopPropagation();
        });
    }
}

// Sidebar panel hover logic for two icons
function setupSidebarPanels() {
    // ...existing code...
    const icons = [
        { icon: document.querySelector('.sidebar-icon[data-panel="mode"]'), panel: document.getElementById('panel-mode') },
        { icon: document.querySelector('.sidebar-icon[data-panel="series"]'), panel: document.getElementById('panel-series') }
    ];
    let panelTimeout = null;
    icons.forEach(({icon, panel}) => {
        if (!icon || !panel) return;
    // ...existing code...
        icon.addEventListener('mouseenter', (e) => {
            // ...existing code...
            document.querySelectorAll('.floating-panel').forEach(p => p.classList.remove('active'));
            if (panel) {
                const rect = icon.getBoundingClientRect();
                const sidebarWidth = icon.parentElement.offsetWidth;
                panel.style.display = 'block';
                const panelHeight = panel.offsetHeight || 480;
                panel.style.display = '';
                let top = rect.top + window.scrollY + rect.height/2 - panelHeight/2;
                top = Math.max(16, Math.min(top, window.innerHeight - panelHeight - 16));
                panel.style.left = sidebarWidth + 'px';
                panel.style.top = top + 'px';
                panel.classList.add('active');
                icon.classList.add('active');
            }
        });
        icon.addEventListener('mouseleave', () => {
            panelTimeout = setTimeout(() => {
                if (panel) panel.classList.remove('active');
                icon.classList.remove('active');
            }, 200);
        });
        if (panel) {
            panel.addEventListener('mouseenter', () => {
                clearTimeout(panelTimeout);
                panel.classList.add('active');
                icon.classList.add('active');
            });
            panel.addEventListener('mouseleave', () => {
                panel.classList.remove('active');
                icon.classList.remove('active');
            });
        }
    });
}

// Custom wheel handler for sidebar and chart
function setupCustomWheel() {
    function handleWheel(e) {
        // Always block horizontal scroll (deltaX) to prevent browser history navigation
        if (Math.abs(e.deltaX) > 0) {
            e.preventDefault();
            return;
        }
        // Only pan if NO modifier keys are held (pure scroll)
        if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) {
            // Do not pan chart if any modifier is held
            return;
        }
        // Only pan if chart is initialized and vertical scroll
        if (window.casinoChart && typeof casinoChart.dispatchAction === 'function' && Math.abs(e.deltaY) > 0) {
            const pan = e.deltaY;
            const option = casinoChart.getOption();
            const dz = option.dataZoom && option.dataZoom[0];
            if (dz) {
                const total = option.xAxis[0].data.length;
                const windowSize = Math.round((dz.end - dz.start) / 100 * total);
                // Pan by 5% of window size per wheel event
                const panStep = Math.max(1, Math.round(windowSize * 0.05));
                let start = Math.round(dz.start / 100 * (total - 1));
                let end = Math.round(dz.end / 100 * (total - 1));
                if (pan > 0) {
                    // Pan right
                    start = Math.min(total - windowSize, start + panStep);
                    end = Math.min(total - 1, end + panStep);
                } else {
                    // Pan left
                    start = Math.max(0, start - panStep);
                    end = Math.max(windowSize - 1, end - panStep);
                }
                const newStart = (start / (total - 1)) * 100;
                const newEnd = (end / (total - 1)) * 100;
                casinoChart.dispatchAction({
                    type: 'dataZoom',
                    start: newStart,
                    end: newEnd
                });
                e.preventDefault();
            }
        }
    }
    const sidebar = document.querySelector('.sidebar');
    const chart = document.getElementById('casinoChart');
    if (sidebar) sidebar.addEventListener('wheel', handleWheel, { passive: false });
    if (chart) chart.addEventListener('wheel', handleWheel, { passive: false });
}

// Resize chart on window resize
function setupChartResize(chart) {
    window.addEventListener('resize', () => {
        if (chart && typeof chart.resize === 'function') {
            chart.resize();
        }
    });
}

export function setupUserControls(chart) {
    preventDefaultScrolls();
    setupAboutModal();
    setupSidebarPanels();
    setupCustomWheel();
    setupChartResize(chart);
}

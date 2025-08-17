// chartHandler.js
// Handles ECharts initialization and updates

// Shared color palette for all chart and UI coloring
const BASE_COLORS = [ 
    '#FFD600', // Galaxy - Vivid Yellow
    '#00E676', // SJM - Bright Green
    '#FF1744', // Wynn - Vivid Red
    '#2979FF', // Sands - Bright Blue
    '#F500A3', // MGM - Magenta
    '#FF9100', // Melco - Orange
    '#00B8D4', // Hang Seng - Cyan
    '#C51162', // Shanghai - Deep Pink
    '#AEEA00'  // Shenzhen - Lime
];
// console.log('[chartHandler.js] loaded'); // Removed debug statement
function hexToRgba(hex, alpha) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.split('').map(x => x + x).join('');
    const num = parseInt(hex, 16);
    const r = (num >> 16) & 255;
    const g = (num >> 8) & 255;
    const b = num & 255;
    return `rgba(${r},${g},${b},${alpha})`;
}
export function getColor(idx) {
    return hexToRgba(BASE_COLORS[idx % BASE_COLORS.length], 0.9);
}

function prepareEChartsOption(config, data, symbolState, selectedSymbols, normalized, indexed, opts = {}) {
    console.log('[minimap][debug] ENTER prepareEChartsOption');
    // Helper for K/M/B formatting
    function formatKMB(val) {
        if (val == null || isNaN(val)) return '';
        if (Math.abs(val) >= 1e12) return (val / 1e12).toFixed(1) + 't';
        if (Math.abs(val) >= 1e9) return (val / 1e9).toFixed(1) + 'b';
        if (Math.abs(val) >= 1e6) return (val / 1e6).toFixed(1) + 'm';
        if (Math.abs(val) >= 1e3) return (val / 1e3).toFixed(1) + 'k';
        return Number(val).toFixed(1);
    }
    // Always use the full union of all dates from all symbols for a stable x-axis
    // Generate a complete calendar date range from min to max date in the data
    let minDate = null, maxDate = null;
    Object.values(data).forEach(symbolData => {
        Object.keys(symbolData).forEach(date => {
            const d = new Date(date);
            if (!minDate || d < minDate) minDate = d;
            if (!maxDate || d > maxDate) maxDate = d;
        });
    });
    function formatDate(d) {
        const m = (d.getMonth() + 1).toString().padStart(2, '0');
        const day = d.getDate().toString().padStart(2, '0');
        return `${d.getFullYear()}-${m}-${day}`;
    }
    const sortedDates = [];
    if (minDate && maxDate) {
        for (let d = new Date(minDate); d <= maxDate; d.setDate(d.getDate() + 1)) {
            sortedDates.push(formatDate(d));
        }
    // Debug log after sortedDates is populated
    console.log('[minimap][debug] after sortedDates populated:', sortedDates);
    }
    // Compute y-axis min/max based on visible (non-null) values in the current window for selected series
    let yMin = undefined, yMax = undefined;
    if (normalized) {
        yMin = 0;
        yMax = 1.05;
    } else if (indexed) {
        yMin = 0;
        yMax = undefined;
    } else if (selectedSymbols.length > 0) {
        let windowRange = opts.windowRange;
        if (!windowRange && typeof opts.getCurrentWindowRange === 'function') {
            windowRange = opts.getCurrentWindowRange();
        }
        if (!windowRange) windowRange = [0, sortedDates.length - 1];
        let allVisible = [];
        selectedSymbols.filter(symbol => data[symbol]).forEach(symbol => {
            const entries = Object.entries(data[symbol]);
            const dateToValue = Object.fromEntries(entries.map(([date, v]) => [date, v['value'] ?? null]));
            let values = sortedDates.map(date => dateToValue[date] ?? null);
            values = values.slice(windowRange[0], windowRange[1] + 1);
            allVisible.push(...values.filter(v => v != null && isFinite(v)));
        });
        if (allVisible.length > 0) {
            yMin = Math.min(...allVisible);
            yMax = Math.max(...allVisible);
            if (yMin === yMax) {
                yMin = yMin * 0.98;
                yMax = yMax * 1.02;
            }
        } else {
            yMin = null;
            yMax = null;
        }
    }
    // Prepare persistent series for all possible symbols (except 'events')
    const allSymbols = (config.symbols || []).map(item => item.field_name).filter(s => s !== 'events');
    // Build symbolNames lookup
    const symbolNames = {};
    (config.symbols || []).forEach(item => { symbolNames[item.field_name] = item.desc || item.field_name; });
    const series = allSymbols.map((symbol) => {
        if (!data[symbol]) return null;
        const isEventFeature = (config.symbols || []).some(item => item.field_name === symbol && (item.category || '').toUpperCase() === 'EVENTS');
        const entries = Object.entries(data[symbol]);
        const dateToValue = Object.fromEntries(entries.map(([date, v]) => [date, v['value'] ?? null]));
        let values = sortedDates.map(date => dateToValue[date] ?? null);
        let actualValues = values.slice();
        let useNormalized = !isEventFeature && normalized;
        let useIndexed = !isEventFeature && indexed;
        let yAxisIndex = isEventFeature ? 1 : 0;
        if (useNormalized && values.filter(v => v != null).length > 0) {
            let windowRange = opts.windowRange || [0, sortedDates.length - 1];
            let windowValues = values.slice(windowRange[0], windowRange[1] + 1).filter(v => v != null && isFinite(v));
            let min = Math.min(...windowValues);
            let max = Math.max(...windowValues);
            if (min === max) {
                min = min * 0.98;
                max = max * 1.02;
            }
            values = values.map(v => (v == null || !isFinite(v)) ? null : (v - min) / (max - min));
        } else if (useIndexed && values.filter(v => v != null).length > 0 && opts.windowRange) {
            let windowRange = opts.windowRange;
            let baseIdx = windowRange[0];
            let base = values[baseIdx];
            if (base == null || !isFinite(base)) {
                for (let i = baseIdx; i <= windowRange[1]; ++i) {
                    if (values[i] != null && isFinite(values[i])) {
                        base = values[i];
                        baseIdx = i;
                        break;
                    }
                }
            }
            if (base != null && isFinite(base) && base !== 0) {
                values = values.map(v => (v == null || !isFinite(v)) ? null : v / base);
            }
        }
        const isSelected = selectedSymbols.includes(symbol);
        const colorIdx = symbolState[symbol] ? symbolState[symbol].colorIdx : 0;
        return {
            name: symbolNames[symbol] + ' (' + symbol + ')',
            type: 'line',
            smooth: window.smoothLineEnabled === true,
            data: isSelected ? values : [],
            yAxisIndex: yAxisIndex,
            showSymbol: true,
            symbol: 'circle',
            symbolSize: 10,
            symbolKeepAspect: true,
            connectNulls: true,
            lineStyle: { width: 2, color: getColor(colorIdx) },
            itemStyle: { color: getColor(colorIdx) },
            emphasis: { focus: 'series' },
            clip: false,
            tooltip: {
                valueFormatter: function (value, i) {
                    if ((useNormalized || useIndexed) && typeof value === 'number' && typeof actualValues[i] === 'number') {
                        return value.toFixed(3) + ' (actual: ' + formatKMB(actualValues[i]) + ')';
                    } else if (typeof value === 'number') {
                        return formatKMB(value);
                    } else {
                        return 'N/A';
                    }
                }
            },
            universalTransition: { enabled: true, seriesKey: 'name' }
        };
    }).filter(Boolean);
    // Only add event bar + dotted line series if 'events' is selected
    if (selectedSymbols.includes('events') && data.events) {
        let eventValues = sortedDates.map(date => {
            const ev = data.events[date];
            if (ev && typeof ev.value === 'number') return ev.value;
            return null;
        });
        if (normalized && eventValues.filter(v => v != null).length > 0) {
            let windowRange = opts.windowRange || [0, sortedDates.length - 1];
            let windowVals = eventValues.slice(windowRange[0], windowRange[1] + 1).filter(v => v != null && isFinite(v));
            let min = Math.min(...windowVals);
            let max = Math.max(...windowVals);
            if (min === max) {
                min = min * 0.98;
                max = max * 1.02;
            }
            eventValues = eventValues.map(v => (v == null || !isFinite(v)) ? null : (v - min) / (max - min));
        } else if (indexed && eventValues.filter(v => v != null).length > 0 && opts.windowRange) {
            let windowRange = opts.windowRange;
            let baseIdx = windowRange[0];
            let base = eventValues[baseIdx];
            if (base == null || !isFinite(base)) {
                for (let i = baseIdx; i <= windowRange[1]; ++i) {
                    if (eventValues[i] != null && isFinite(eventValues[i])) {
                        base = eventValues[i];
                        baseIdx = i;
                        break;
                    }
                }
            }
            if (base != null && isFinite(base) && base !== 0) {
                eventValues = eventValues.map(v => (v == null || !isFinite(v)) ? null : v / base);
            }
        }
        const eventColor = '#00bcd4';
        series.push({
            name: 'Event Impact',
            type: 'bar',
            data: selectedSymbols.includes('events') ? eventValues : [],
            yAxisIndex: 1,
            barMinWidth: 8,
            barMaxWidth: 24,
            itemStyle: { color: eventColor, opacity: 0.45 },
            emphasis: { focus: 'series' },
            z: 2,
            legendHoverLink: true,
            clip: false,
            universalTransition: { enabled: true, seriesKey: 'name' }
        });
        series.push({
            name: 'Event Impact',
            type: 'line',
            data: selectedSymbols.includes('events') ? eventValues : [],
            yAxisIndex: 1,
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 10,
            symbolKeepAspect: true,
            connectNulls: true,
            smooth: window.smoothLineEnabled === true,
            lineStyle: { width: 2, color: eventColor, type: 'solid' },
            itemStyle: { color: eventColor },
            emphasis: { focus: 'series' },
            z: 3,
            legendHoverLink: true,
            clip: false,
            universalTransition: { enabled: true, seriesKey: 'name' }
        });
    }
    // --- Minimap shadow calculation block ---
    let dataShadowArr = null;
    const visibleSymbols = selectedSymbols.filter(symbol => symbol !== 'events' && data[symbol]);
    if (visibleSymbols.length > 0) {
        // Always use max of forward-filled values for all visible series
        const firstVals = {};
        for (let symbol of visibleSymbols) {
            const symbolData = data[symbol];
            for (let date of sortedDates) {
                if (symbolData[date] && symbolData[date].value != null && isFinite(symbolData[date].value)) {
                    firstVals[symbol] = symbolData[date].value;
                    break;
                }
            }
        }
        const lastKnown = { ...firstVals };
        dataShadowArr = sortedDates.map((date, idx) => {
            let max = null;
            for (let symbol of visibleSymbols) {
                const symbolData = data[symbol];
                let val = undefined;
                if (symbolData[date] && symbolData[date].value != null && isFinite(symbolData[date].value)) {
                    val = symbolData[date].value;
                    lastKnown[symbol] = val;
                } else if (lastKnown[symbol] != null && isFinite(lastKnown[symbol])) {
                    val = lastKnown[symbol];
                }
                if (val != null && isFinite(val)) {
                    if (max == null || val > max) max = val;
                }
            }
            return max == null ? 0 : max;
        });
    }
    const defaultMonths = 36;
    const defaultDays = defaultMonths * 21;
    const defaultWindow = sortedDates.length > defaultDays ? Math.round((sortedDates.length - defaultDays) / sortedDates.length * 100) : 0;
    const globalFontSize = 16;

    console.log('[minimap][debug] dataShadowArr: ', dataShadowArr);
    if (Array.isArray(dataShadowArr)) {
        const isCorrectLength = dataShadowArr.length === sortedDates.length;
        const allNumbers = dataShadowArr.every(x => typeof x === 'number' && isFinite(x));
        const hasNull = dataShadowArr.some(x => x === null);
        const hasUndefined = dataShadowArr.some(x => x === undefined);
        const hasNaN = dataShadowArr.some(x => typeof x === 'number' && isNaN(x));
        console.log('[minimap][debug] dataShadowArr checks:', {
            isArray: true,
            isCorrectLength,
            allNumbers,
            hasNull,
            hasUndefined,
            hasNaN,
            length: dataShadowArr.length,
            xAxisLength: sortedDates.length
        });
    } else {
        console.log('[minimap][debug] dataShadowArr is not an array:', dataShadowArr);
    }

    return {
        animation: opts.disableAnim ? false : true,
        animationEasing: 'cubicOut',
        animationDuration: opts.disableAnim ? 0 : 600,
        animationEasingUpdate: 'cubicOut',
        animationDurationUpdate: opts.disableAnim ? 0 : 300,
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross',
                crossStyle: {
                    color: '#00bcd4',
                    width: 1.5
                },
                label: {
                    backgroundColor: '#232837',
                    color: '#fff',
                    borderColor: '#00bcd4',
                    borderWidth: 1,
                    fontWeight: 'bold',
                    fontSize: globalFontSize,
                    fontFamily: 'MCI',
                    padding: [6, 16],
                    margin: 0
                }
            },
            backgroundColor: '#232837',
            borderColor: '#fff',
            textStyle: { color: '#fff', fontFamily: 'MCI', fontSize: globalFontSize },
            formatter: function(params) {
                if (!params || !params.length) return '';
                const date = params[0].axisValue;
                let html = '';
                if (selectedSymbols.includes('events') && data.events && data.events[date] && Array.isArray(data.events[date].events) && data.events[date].events.length > 0) {
                    const themeColor = '#00bcd4';
                    let eventList = data.events[date].events.map(ev => {
                        let txt = `<div style=\"margin-bottom:6px;font-size:${globalFontSize}px\">`;
                        Object.entries(ev).forEach(([key, value]) => {
                            const capKey = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                            let displayValue = value;
                            if (typeof value === 'number') {
                                displayValue = value.toFixed(3).replace(/\.0+$/, '').replace(/(\.[0-9]*[1-9])0+$/, '$1');
                            }
                            txt += `<b><span style='color:${themeColor}'>${capKey}</span>:</b> ${typeof value === 'object' ? JSON.stringify(value) : displayValue}<br>`;
                        });
                        txt += '</div>';
                        return txt;
                    }).join('<hr style=\'margin:4px 0;opacity:0.3\'>');
                    html += `<div style='max-width:420px;word-break:break-word;white-space:pre-line;overflow-wrap:anywhere;margin-bottom:8px;font-size:${globalFontSize}px'><b>Events:</b><br>${eventList}</div>`;
                }
                const seen = new Set();
                html += params.filter(param => {
                    const key = param.seriesName + '|' + param.value;
                    if (seen.has(key)) return false;
                    seen.add(key);
                    return true;
                }).map(param => {
                    let val = param.value;
                    let displayVal = val;
                    if (typeof val === 'number') {
                        displayVal = val.toFixed(3).replace(/\.0+$/, '').replace(/(\.[0-9]*[1-9])0+$/, '$1');
                        return `<span style='color:${param.color};font-weight:bold;font-size:${globalFontSize}px'>&#9679;</span> <span style='font-size:${globalFontSize}px'>${param.seriesName}: ${displayVal}</span>`;
                    } else {
                        return `<span style='color:${param.color};font-weight:bold;font-size:${globalFontSize}px'>&#9679;</span> <span style='font-size:${globalFontSize}px'>${param.seriesName}: N/A</span>`;
                    }
                }).join('<br>');
                return html;
            }
        },
        legend: { show: false, textStyle: { fontFamily: 'MCI' } },
        grid: { left: 52, right: 52, top: 85, bottom: 28 },
        dataZoom: [
            {
                type: 'slider',
                show: true,
                xAxisIndex: 0,
                start: defaultWindow,
                end: 100,
                height: 22,
                bottom: null,
                top: 0,
                backgroundColor: '#232837',
                borderColor: '#333',
                fillerColor: 'rgba(0,188,212,0.18)',
                handleIcon: 'M8.7,11.3v-8.6h2.6v8.6H8.7z',
                handleSize: '120%',
                moveHandleSize: '100%',
                showDetail: true,
                handleStyle: { color: '#00bcd4' },
                textStyle: { color: '#fff' },
                minValueSpan: 30,
                showDataShadow: true,
                dataShadow: dataShadowArr,
                dataBackground: {
                    lineStyle: { color: '#FFD600', opacity: 1 },
                    areaStyle: { color: 'rgba(255,214,0,0.8)' }
                }
            },
            {
                type: 'inside',
                xAxisIndex: 0,
                zoomOnMouseWheel: 'shift',
                moveOnMouseWheel: true,
                moveOnMouseMove: true,
                minValueSpan: 30
            }
        ],
        xAxis: {
            type: 'category',
            data: sortedDates,
            axisLabel: {
                rotate: 0,
                color: 'rgba(255,255,255,0.8)',
                fontWeight: 500,
                interval: 'auto',
                minInterval: 1,
                hideOverlap: true,
                fontFamily: 'MCI',
                letterSpacing: 2,
                fontSize: 16,
                formatter: function(value, index) {
                    const total = sortedDates.length;
                    if (this && this.axis && typeof this.axis.getViewLabels === 'function') {
                        const labels = this.axis.getViewLabels();
                        if (labels.length < 4) {
                            const step = Math.max(1, Math.floor(total / 4));
                            if (index % step !== 0 && index !== total - 1 && index !== 0) return '';
                        }
                    }
                    return value;
                }
            },
            axisLine: { lineStyle: { color: 'rgba(255,255,255,0.8)' } }
        },
        yAxis: [
            {
                type: 'value',
                name: normalized ? 'Normalized' : indexed ? 'Indexed' : 'Value',
                position: 'left',
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.8)' } },
                axisLabel: { formatter: v => normalized ? v.toFixed(3) : (typeof v === 'number' ? formatKMB(v) : v), color: 'rgba(255,255,255,0.8)', fontWeight: 500, fontFamily: 'MCI', letterSpacing: 2, fontSize: 16, margin: 8 },
                nameTextStyle: { color: 'rgba(255,255,255,0.8)', fontWeight: 600, fontFamily: 'MCI', letterSpacing: 2, fontSize: 16 },
                nameGap: 16,
                splitLine: { lineStyle: { color: '#333' } },
                min: yMin,
                max: yMax,
                axisPointer: { label: { margin: -8, padding: [6, 8] } }
            },
            {
                type: 'value',
                name: 'Events',
                position: 'right',
                axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.8)' } },
                axisLabel: { formatter: v => typeof v === 'number' ? v.toFixed(2) : v, color: 'rgba(255,255,255,0.8)', fontWeight: 500, fontFamily: 'MCI', letterSpacing: 2, fontSize: 16, margin: 8 },
                nameTextStyle: { color: 'rgba(255,255,255,0.8)', fontWeight: 600, fontFamily: 'MCI', letterSpacing: 2, fontSize: 16 },
                nameGap: 16,
                splitLine: { show: false },
                axisPointer: { label: { margin: -8, padding: [6, 8] } }
            }
        ],
        series: series.map(s => s.type === 'bar' ? { ...s, barMinWidth: 3 } : s)
    };
}


export function initChart(container, config, data, symbolState, options) {
    console.log('[minimap][debug] ENTER initChart');
    const echartsInstance = echarts.init(container);
    const chartOption = prepareEChartsOption(config, data, symbolState, options.selectedSymbols, options.normalized, options.indexed, options);
    echartsInstance.setOption(chartOption);
    return echartsInstance;
}


export function updateChart(chart, config, data, symbolState, options) {
    console.log('[minimap][debug] ENTER updateChart');
    const chartOption = prepareEChartsOption(config, data, symbolState, options.selectedSymbols, options.normalized, options.indexed, options);
    chart.setOption(chartOption, { notMerge: false });
}

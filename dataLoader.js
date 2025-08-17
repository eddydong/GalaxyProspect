// dataLoader.js
// Loads config.json and series data from API, returns { config, data }

export async function loadData() {
    const configRes = await fetch('/static/config.json');
    const config = await configRes.json();
    const dataRes = await fetch('/api/daily');
    const docs = await dataRes.json();
    // Transform to: { symbol: { date: { 'value': value }, ... }, ... }
    const symbolData = {};
    docs.forEach(doc => {
        const date = doc._id;
        const data = doc.data || {};
        Object.keys(data).forEach(symbol => {
            if (!symbolData[symbol]) symbolData[symbol] = {};
            let val = data[symbol];
            if (val && typeof val === 'object' && 'value' in val) {
                val = val.value;
            }
            symbolData[symbol][date] = data[symbol];
        });
    });
    return { config, data: symbolData };
}

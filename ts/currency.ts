// MCP Currency Exchange Server
// Exchange rates using free APIs (exchangerate.host, frankfurter.app)

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const API_BASE = 'https://api.frankfurter.app';

interface CurrencyResult<T = unknown> {
    success: boolean;
    data?: T;
    error?: string;
}

async function fetchJson<T>(url: string): Promise<CurrencyResult<T>> {
    try {
        const response = await fetch(url, {
            headers: {
                Accept: 'application/json',
                'User-Agent': 'Flopsy-Currency-MCP/1.0',
            },
        });

        if (!response.ok) {
            return { success: false, error: `HTTP ${response.status}: ${response.statusText}` };
        }

        const data = (await response.json()) as T;
        return { success: true, data };
    } catch (err) {
        return { success: false, error: (err as Error).message };
    }
}

function formatResult<T>(result: CurrencyResult<T>): {
    content: Array<{ type: 'text'; text: string }>;
} {
    if (!result.success) {
        return {
            content: [{ type: 'text', text: JSON.stringify({ error: result.error }) }],
        };
    }
    return {
        content: [{ type: 'text', text: JSON.stringify(result.data, null, 2) }],
    };
}

interface LatestRates {
    base: string;
    date: string;
    rates: Record<string, number>;
}

async function getLatestRates(base: string, symbols?: string[]): Promise<CurrencyResult> {
    let url = `${API_BASE}/latest?from=${base.toUpperCase()}`;
    if (symbols && symbols.length > 0) {
        url += `&to=${symbols.map((s) => s.toUpperCase()).join(',')}`;
    }

    const result = await fetchJson<LatestRates>(url);

    if (!result.success) return result;

    const rates = Object.entries(result.data!.rates).map(([currency, rate]) => ({
        currency,
        rate,
        inverse: (1 / rate).toFixed(6),
    }));

    return {
        success: true,
        data: {
            base: result.data!.base,
            date: result.data!.date,
            count: rates.length,
            rates,
            timestamp: new Date().toISOString(),
        },
    };
}

async function convert(from: string, to: string, amount: number): Promise<CurrencyResult> {
    const url = `${API_BASE}/latest?amount=${amount}&from=${from.toUpperCase()}&to=${to.toUpperCase()}`;

    const result = await fetchJson<LatestRates>(url);

    if (!result.success) return result;

    const converted = result.data!.rates[to.toUpperCase()];
    if (converted === undefined) {
        return { success: false, error: `Currency ${to.toUpperCase()} not found` };
    }
    const rate = converted / amount;

    return {
        success: true,
        data: {
            from: from.toUpperCase(),
            to: to.toUpperCase(),
            amount,
            converted,
            rate,
            date: result.data!.date,
            formatted: `${amount} ${from.toUpperCase()} = ${converted.toFixed(2)} ${to.toUpperCase()}`,
        },
    };
}

interface HistoricalRates {
    base: string;
    start_date: string;
    end_date: string;
    rates: Record<string, Record<string, number>>;
}

async function getHistorical(
    base: string,
    target: string,
    startDate: string,
    endDate: string,
): Promise<CurrencyResult> {
    const url = `${API_BASE}/${startDate}..${endDate}?from=${base.toUpperCase()}&to=${target.toUpperCase()}`;

    const result = await fetchJson<HistoricalRates>(url);

    if (!result.success) return result;

    const history = Object.entries(result.data!.rates).map(([date, rates]) => ({
        date,
        rate: rates[target.toUpperCase()],
    }));

    // Calculate stats - filter out undefined values
    const rateValues = history.map((h) => h.rate).filter((r): r is number => r !== undefined);

    if (rateValues.length === 0) {
        return { success: false, error: 'No rate data found for the specified period' };
    }

    const firstRate = rateValues[0]!;
    const lastRate = rateValues[rateValues.length - 1]!;
    const change = ((lastRate - firstRate) / firstRate) * 100;

    return {
        success: true,
        data: {
            base: base.toUpperCase(),
            target: target.toUpperCase(),
            period: { start: startDate, end: endDate },
            dataPoints: history.length,
            summary: {
                startRate: firstRate,
                endRate: lastRate,
                change: change.toFixed(2) + '%',
                high: Math.max(...rateValues).toFixed(4),
                low: Math.min(...rateValues).toFixed(4),
                average: (rateValues.reduce((a, b) => a + b, 0) / rateValues.length).toFixed(4),
            },
            history,
        },
    };
}

interface CurrencyList {
    [key: string]: string;
}

async function getCurrencies(): Promise<CurrencyResult> {
    const result = await fetchJson<CurrencyList>(`${API_BASE}/currencies`);

    if (!result.success) return result;

    const currencies = Object.entries(result.data!).map(([code, name]) => ({
        code,
        name,
    }));

    // Group by common categories
    const major = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'CNY'];
    const majorCurrencies = currencies.filter((c) => major.includes(c.code));
    const otherCurrencies = currencies.filter((c) => !major.includes(c.code));

    return {
        success: true,
        data: {
            total: currencies.length,
            major: majorCurrencies,
            other: otherCurrencies,
        },
    };
}

export function createCurrencyMcpServer() {
    const server = new McpServer({
        name: 'currency-server',
        version: '1.0.0',
    });

    server.registerTool(
        'currency_rates',
        {
            title: 'Exchange Rates',
            description: 'Get current exchange rates for a base currency.',
            inputSchema: {
                base: z.string().default('USD').describe("Base currency code (e.g., 'USD', 'EUR')"),
                symbols: z
                    .array(z.string())
                    .optional()
                    .describe("Target currencies (e.g., ['EUR', 'GBP']). Leave empty for all."),
            },
        },
        async ({ base, symbols }) => {
            const result = await getLatestRates(base, symbols);
            return formatResult(result);
        },
    );

    server.registerTool(
        'currency_convert',
        {
            title: 'Convert Currency',
            description: 'Convert an amount from one currency to another.',
            inputSchema: {
                from: z.string().describe("Source currency (e.g., 'USD')"),
                to: z.string().describe("Target currency (e.g., 'EUR')"),
                amount: z.number().describe('Amount to convert'),
            },
        },
        async ({ from, to, amount }) => {
            const result = await convert(from, to, amount);
            return formatResult(result);
        },
    );

    server.registerTool(
        'currency_history',
        {
            title: 'Historical Rates',
            description: 'Get historical exchange rates between two currencies.',
            inputSchema: {
                base: z.string().describe("Base currency (e.g., 'USD')"),
                target: z.string().describe("Target currency (e.g., 'EUR')"),
                startDate: z.string().describe("Start date (YYYY-MM-DD, e.g., '2024-01-01')"),
                endDate: z.string().describe("End date (YYYY-MM-DD, e.g., '2024-12-31')"),
            },
        },
        async ({ base, target, startDate, endDate }) => {
            const result = await getHistorical(base, target, startDate, endDate);
            return formatResult(result);
        },
    );

    server.registerTool(
        'currency_list',
        {
            title: 'List Currencies',
            description: 'Get list of all supported currencies with their names.',
            inputSchema: {},
        },
        async () => {
            const result = await getCurrencies();
            return formatResult(result);
        },
    );

    server.registerTool(
        'currency_multi',
        {
            title: 'Multi Currency Convert',
            description: 'Convert an amount to multiple currencies at once.',
            inputSchema: {
                from: z.string().describe("Source currency (e.g., 'USD')"),
                amount: z.number().describe('Amount to convert'),
                to: z.array(z.string()).describe("Target currencies (e.g., ['EUR', 'GBP', 'JPY'])"),
            },
        },
        async ({ from, amount, to }) => {
            const url = `${API_BASE}/latest?amount=${amount}&from=${from.toUpperCase()}&to=${to.map((s) => s.toUpperCase()).join(',')}`;
            const result = await fetchJson<LatestRates>(url);

            if (!result.success) return formatResult(result);

            const conversions = Object.entries(result.data!.rates).map(([currency, value]) => ({
                currency,
                value: value.toFixed(2),
                formatted: `${value.toFixed(2)} ${currency}`,
            }));

            return formatResult({
                success: true,
                data: {
                    from: from.toUpperCase(),
                    amount,
                    date: result.data!.date,
                    conversions,
                },
            });
        },
    );

    return server;
}

async function main() {
    const server = createCurrencyMcpServer();

    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('[MCP] Currency started');
}

// Run if executed directly
const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
    main().catch((error) => {
        console.error('[MCP Currency Server] Fatal error:', error);
        process.exit(1);
    });
}

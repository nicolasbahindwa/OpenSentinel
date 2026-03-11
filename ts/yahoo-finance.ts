// MCP Yahoo Finance Server
// Stock quotes, historical data, and company info using yahoo-finance2
// https://github.com/gadicc/node-yahoo-finance2

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import YahooFinance from 'yahoo-finance2';

const yahooFinance = new YahooFinance();

interface FinanceResult<T = unknown> {
    success: boolean;
    data?: T;
    error?: string;
}

function formatResult<T>(result: FinanceResult<T>): {
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

async function getQuote(symbol: string): Promise<FinanceResult> {
    try {
        const quote = await yahooFinance.quote(symbol);

        if (!quote) {
            return { success: false, error: `No quote found for ${symbol}` };
        }

        return {
            success: true,
            data: {
                symbol: quote.symbol,
                name: quote.shortName || quote.longName,
                price: quote.regularMarketPrice,
                change: quote.regularMarketChange,
                changePercent: quote.regularMarketChangePercent,
                previousClose: quote.regularMarketPreviousClose,
                open: quote.regularMarketOpen,
                dayHigh: quote.regularMarketDayHigh,
                dayLow: quote.regularMarketDayLow,
                volume: quote.regularMarketVolume,
                avgVolume: quote.averageDailyVolume3Month,
                marketCap: quote.marketCap,
                peRatio: quote.trailingPE,
                eps: quote.epsTrailingTwelveMonths,
                dividendYield: quote.dividendYield,
                fiftyTwoWeekHigh: quote.fiftyTwoWeekHigh,
                fiftyTwoWeekLow: quote.fiftyTwoWeekLow,
                exchange: quote.exchange,
                currency: quote.currency,
                marketState: quote.marketState,
                timestamp: new Date().toISOString(),
            },
        };
    } catch (err) {
        return { success: false, error: (err as Error).message };
    }
}

async function getHistorical(
    symbol: string,
    period: string,
    interval: string,
): Promise<FinanceResult> {
    try {
        // Map period to date range
        const now = new Date();
        let startDate: Date;

        switch (period) {
            case '1d':
                startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                break;
            case '5d':
                startDate = new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000);
                break;
            case '1mo':
                startDate = new Date(now.setMonth(now.getMonth() - 1));
                break;
            case '3mo':
                startDate = new Date(now.setMonth(now.getMonth() - 3));
                break;
            case '6mo':
                startDate = new Date(now.setMonth(now.getMonth() - 6));
                break;
            case '1y':
                startDate = new Date(now.setFullYear(now.getFullYear() - 1));
                break;
            case '2y':
                startDate = new Date(now.setFullYear(now.getFullYear() - 2));
                break;
            case '5y':
                startDate = new Date(now.setFullYear(now.getFullYear() - 5));
                break;
            default:
                startDate = new Date(now.setMonth(now.getMonth() - 1));
        }

        const historical = await yahooFinance.chart(symbol, {
            period1: startDate,
            period2: new Date(),
            interval: interval as '1d' | '1wk' | '1mo',
        });

        if (!historical || !historical.quotes || historical.quotes.length === 0) {
            return { success: false, error: `No historical data for ${symbol}` };
        }

        const quotes = historical.quotes.map((q) => ({
            date: q.date?.toISOString().split('T')[0],
            open: q.open,
            high: q.high,
            low: q.low,
            close: q.close,
            volume: q.volume,
        }));

        // Calculate summary stats
        const closes = quotes.map((q) => q.close).filter((c): c is number => c != null);
        const firstClose = closes[0];
        const lastClose = closes[closes.length - 1];
        const periodChange = firstClose && lastClose ? lastClose - firstClose : null;
        const periodChangePercent =
            firstClose && periodChange ? (periodChange / firstClose) * 100 : null;

        return {
            success: true,
            data: {
                symbol,
                period,
                interval,
                dataPoints: quotes.length,
                summary: {
                    startPrice: firstClose,
                    endPrice: lastClose,
                    change: periodChange?.toFixed(2),
                    changePercent: periodChangePercent?.toFixed(2) + '%',
                    high: Math.max(...closes),
                    low: Math.min(...closes),
                },
                quotes,
            },
        };
    } catch (err) {
        return { success: false, error: (err as Error).message };
    }
}

async function searchSymbol(query: string, limit: number): Promise<FinanceResult> {
    try {
        const results = await yahooFinance.search(query);

        if (!results || !results.quotes || results.quotes.length === 0) {
            return { success: false, error: `No results found for "${query}"` };
        }

        const symbols = results.quotes.slice(0, limit).map((q) => ({
            symbol: q.symbol,
            name: q.shortname || q.longname,
            type: q.quoteType,
            exchange: q.exchange,
            industry: q.industry,
        }));

        return {
            success: true,
            data: {
                query,
                count: symbols.length,
                results: symbols,
            },
        };
    } catch (err) {
        return { success: false, error: (err as Error).message };
    }
}

async function getQuoteSummary(symbol: string): Promise<FinanceResult> {
    try {
        const summary = await yahooFinance.quoteSummary(symbol, {
            modules: ['summaryProfile', 'summaryDetail', 'financialData', 'defaultKeyStatistics'],
        });

        if (!summary) {
            return { success: false, error: `No summary for ${symbol}` };
        }

        const profile = summary.summaryProfile;
        const detail = summary.summaryDetail;
        const financial = summary.financialData;
        const stats = summary.defaultKeyStatistics;

        return {
            success: true,
            data: {
                symbol,
                company: {
                    name: profile?.longBusinessSummary?.slice(0, 500),
                    sector: profile?.sector,
                    industry: profile?.industry,
                    website: profile?.website,
                    employees: profile?.fullTimeEmployees,
                    country: profile?.country,
                    city: profile?.city,
                },
                valuation: {
                    marketCap: detail?.marketCap,
                    enterpriseValue: stats?.enterpriseValue,
                    peRatio: detail?.trailingPE,
                    forwardPE: detail?.forwardPE,
                    pegRatio: stats?.pegRatio,
                    priceToBook: stats?.priceToBook,
                    priceToSales: stats?.priceToSalesTrailing12Months,
                },
                financials: {
                    revenue: financial?.totalRevenue,
                    revenuePerShare: financial?.revenuePerShare,
                    grossMargin: financial?.grossMargins,
                    operatingMargin: financial?.operatingMargins,
                    profitMargin: financial?.profitMargins,
                    returnOnEquity: financial?.returnOnEquity,
                    returnOnAssets: financial?.returnOnAssets,
                    debtToEquity: financial?.debtToEquity,
                    currentRatio: financial?.currentRatio,
                },
                dividend: {
                    yield: detail?.dividendYield,
                    rate: detail?.dividendRate,
                    payoutRatio: detail?.payoutRatio,
                    exDate: detail?.exDividendDate,
                },
                trading: {
                    beta: detail?.beta,
                    fiftyDayAvg: detail?.fiftyDayAverage,
                    twoHundredDayAvg: detail?.twoHundredDayAverage,
                    avgVolume: detail?.averageVolume,
                    avgVolume10Day: detail?.averageVolume10days,
                },
                timestamp: new Date().toISOString(),
            },
        };
    } catch (err) {
        return { success: false, error: (err as Error).message };
    }
}

async function getMultipleQuotes(symbols: string[]): Promise<FinanceResult> {
    try {
        const quotes = await Promise.all(
            symbols.map(async (symbol) => {
                try {
                    const quote = await yahooFinance.quote(symbol);
                    return {
                        symbol: quote.symbol,
                        name: quote.shortName,
                        price: quote.regularMarketPrice,
                        change: quote.regularMarketChange,
                        changePercent: quote.regularMarketChangePercent,
                        volume: quote.regularMarketVolume,
                        marketCap: quote.marketCap,
                    };
                } catch {
                    return { symbol, error: 'Failed to fetch' };
                }
            }),
        );

        return {
            success: true,
            data: {
                count: quotes.length,
                quotes,
                timestamp: new Date().toISOString(),
            },
        };
    } catch (err) {
        return { success: false, error: (err as Error).message };
    }
}

async function getTrending(): Promise<FinanceResult> {
    try {
        const trending = await yahooFinance.trendingSymbols('US', { count: 10 });

        if (!trending || !trending.quotes || trending.quotes.length === 0) {
            return { success: false, error: 'No trending symbols found' };
        }

        // Get quotes for trending symbols
        const symbols = trending.quotes.map((q) => q.symbol);
        const quotes = await getMultipleQuotes(symbols);

        return quotes;
    } catch (err) {
        return { success: false, error: (err as Error).message };
    }
}

export function createYahooFinanceMcpServer() {
    const server = new McpServer({
        name: 'yahoo-finance-server',
        version: '1.0.0',
    });

    server.registerTool(
        'yahoo_finance_quote',
        {
            title: 'Stock Quote',
            description:
                'Get current stock quote with price, change, volume, and key metrics. Use stock symbol (e.g., AAPL, MSFT, GOOGL).',
            inputSchema: {
                symbol: z.string().describe("Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'TSLA')"),
            },
        },
        async ({ symbol }) => {
            const result = await getQuote(symbol.toUpperCase());
            return formatResult(result);
        },
    );

    server.registerTool(
        'yahoo_finance_quotes',
        {
            title: 'Multiple Stock Quotes',
            description:
                'Get quotes for multiple stocks at once. Faster than calling quote multiple times.',
            inputSchema: {
                symbols: z
                    .array(z.string())
                    .describe("Array of ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])"),
            },
        },
        async ({ symbols }) => {
            const result = await getMultipleQuotes(symbols.map((s) => s.toUpperCase()));
            return formatResult(result);
        },
    );

    server.registerTool(
        'yahoo_finance_historical',
        {
            title: 'Historical Stock Data',
            description:
                'Get historical price data for a stock. Returns OHLCV (open, high, low, close, volume).',
            inputSchema: {
                symbol: z.string().describe("Stock ticker symbol (e.g., 'AAPL')"),
                period: z
                    .enum(['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y'])
                    .default('1mo')
                    .describe('Time period (default: 1mo)'),
                interval: z
                    .enum(['1d', '1wk', '1mo'])
                    .default('1d')
                    .describe('Data interval (default: 1d)'),
            },
        },
        async ({ symbol, period, interval }) => {
            const result = await getHistorical(symbol.toUpperCase(), period, interval);
            return formatResult(result);
        },
    );

    server.registerTool(
        'yahoo_finance_search',
        {
            title: 'Search Stocks',
            description:
                'Search for stock symbols by company name or ticker. Use to find the correct symbol.',
            inputSchema: {
                query: z
                    .string()
                    .describe("Company name or partial symbol (e.g., 'Apple', 'Tesla')"),
                limit: z.number().default(5).describe('Max results (default: 5)'),
            },
        },
        async ({ query, limit }) => {
            const result = await searchSymbol(query, limit);
            return formatResult(result);
        },
    );

    server.registerTool(
        'yahoo_finance_summary',
        {
            title: 'Company Summary',
            description:
                'Get detailed company info: profile, valuation metrics, financials, and dividend data.',
            inputSchema: {
                symbol: z.string().describe("Stock ticker symbol (e.g., 'AAPL')"),
            },
        },
        async ({ symbol }) => {
            const result = await getQuoteSummary(symbol.toUpperCase());
            return formatResult(result);
        },
    );

    server.registerTool(
        'yahoo_finance_trending',
        {
            title: 'Trending Stocks',
            description: 'Get currently trending stocks in the US market.',
            inputSchema: {},
        },
        async () => {
            const result = await getTrending();
            return formatResult(result);
        },
    );

    server.registerTool(
        'yahoo_finance_market',
        {
            title: 'Market Overview',
            description: 'Get overview of major market indices (S&P 500, Dow, Nasdaq, etc.).',
            inputSchema: {},
        },
        async () => {
            const indices = ['^GSPC', '^DJI', '^IXIC', '^RUT', '^VIX'];
            const result = await getMultipleQuotes(indices);

            if (result.success && result.data) {
                // Rename symbols to friendly names
                const nameMap: Record<string, string> = {
                    '^GSPC': 'S&P 500',
                    '^DJI': 'Dow Jones',
                    '^IXIC': 'Nasdaq',
                    '^RUT': 'Russell 2000',
                    '^VIX': 'VIX',
                };

                const data = result.data as { quotes: Array<{ symbol: string; name?: string }> };
                data.quotes = data.quotes.map((q) => {
                    const name = nameMap[q.symbol] || q.name;
                    return name ? { ...q, name } : q;
                });
            }

            return formatResult(result);
        },
    );

    return server;
}

async function main() {
    const server = createYahooFinanceMcpServer();

    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('[MCP] Yahoo Finance started');
}

// Run if executed directly
const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
    main().catch((error) => {
        console.error('[MCP Yahoo Finance Server] Fatal error:', error);
        process.exit(1);
    });
}

// MCP Crypto Server
// Cryptocurrency data using CoinGecko API (free, no API key required)
// https://www.coingecko.com/en/api

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const API_BASE = 'https://api.coingecko.com/api/v3';

interface CryptoResult<T = unknown> {
    success: boolean;
    data?: T;
    error?: string;
}

async function fetchJson<T>(endpoint: string): Promise<CryptoResult<T>> {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                Accept: 'application/json',
                'User-Agent': 'Flopsy-Crypto-MCP/1.0',
            },
        });

        if (!response.ok) {
            if (response.status === 429) {
                return { success: false, error: 'Rate limit exceeded. Try again in a minute.' };
            }
            return { success: false, error: `HTTP ${response.status}: ${response.statusText}` };
        }

        const data = (await response.json()) as T;
        return { success: true, data };
    } catch (err) {
        return { success: false, error: (err as Error).message };
    }
}

function formatResult<T>(result: CryptoResult<T>): {
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

interface CoinPrice {
    [key: string]: {
        usd: number;
        usd_24h_change?: number;
        usd_24h_vol?: number;
        usd_market_cap?: number;
    };
}

async function getPrice(ids: string[], currency = 'usd'): Promise<CryptoResult> {
    const result = await fetchJson<CoinPrice>(
        `/simple/price?ids=${ids.join(',')}&vs_currencies=${currency}&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true`,
    );

    if (!result.success) return result;

    const prices = Object.entries(result.data!).map(([id, data]) => ({
        id,
        price: data.usd,
        change24h: data.usd_24h_change?.toFixed(2) + '%',
        volume24h: data.usd_24h_vol,
        marketCap: data.usd_market_cap,
    }));

    return {
        success: true,
        data: {
            currency,
            count: prices.length,
            prices,
            timestamp: new Date().toISOString(),
        },
    };
}

interface MarketCoin {
    id: string;
    symbol: string;
    name: string;
    current_price: number;
    market_cap: number;
    market_cap_rank: number;
    price_change_percentage_24h: number;
    total_volume: number;
    high_24h: number;
    low_24h: number;
    circulating_supply: number;
    total_supply: number;
    ath: number;
    ath_change_percentage: number;
}

async function getMarkets(limit = 20, currency = 'usd'): Promise<CryptoResult> {
    const result = await fetchJson<MarketCoin[]>(
        `/coins/markets?vs_currency=${currency}&order=market_cap_desc&per_page=${limit}&page=1&sparkline=false`,
    );

    if (!result.success) return result;

    const coins = result.data!.map((coin) => ({
        rank: coin.market_cap_rank,
        id: coin.id,
        symbol: coin.symbol.toUpperCase(),
        name: coin.name,
        price: coin.current_price,
        change24h: coin.price_change_percentage_24h?.toFixed(2) + '%',
        marketCap: coin.market_cap,
        volume24h: coin.total_volume,
        high24h: coin.high_24h,
        low24h: coin.low_24h,
    }));

    return {
        success: true,
        data: {
            currency,
            count: coins.length,
            coins,
            timestamp: new Date().toISOString(),
        },
    };
}

interface SearchResult {
    coins: Array<{
        id: string;
        name: string;
        symbol: string;
        market_cap_rank: number;
        thumb: string;
    }>;
}

async function searchCoins(query: string): Promise<CryptoResult> {
    const result = await fetchJson<SearchResult>(`/search?query=${encodeURIComponent(query)}`);

    if (!result.success) return result;

    const coins = result.data!.coins.slice(0, 10).map((coin) => ({
        id: coin.id,
        symbol: coin.symbol.toUpperCase(),
        name: coin.name,
        rank: coin.market_cap_rank,
    }));

    return {
        success: true,
        data: {
            query,
            count: coins.length,
            coins,
        },
    };
}

interface TrendingResult {
    coins: Array<{
        item: {
            id: string;
            name: string;
            symbol: string;
            market_cap_rank: number;
            price_btc: number;
            data: {
                price: number;
                price_change_percentage_24h: { usd: number };
                market_cap: string;
            };
        };
    }>;
}

async function getTrending(): Promise<CryptoResult> {
    const result = await fetchJson<TrendingResult>('/search/trending');

    if (!result.success) return result;

    const coins = result.data!.coins.map((c) => ({
        id: c.item.id,
        symbol: c.item.symbol.toUpperCase(),
        name: c.item.name,
        rank: c.item.market_cap_rank,
        price: c.item.data?.price,
        change24h: c.item.data?.price_change_percentage_24h?.usd?.toFixed(2) + '%',
    }));

    return {
        success: true,
        data: {
            count: coins.length,
            trending: coins,
            timestamp: new Date().toISOString(),
        },
    };
}

interface CoinDetail {
    id: string;
    symbol: string;
    name: string;
    description: { en: string };
    links: { homepage: string[]; blockchain_site: string[] };
    market_cap_rank: number;
    market_data: {
        current_price: { usd: number };
        market_cap: { usd: number };
        total_volume: { usd: number };
        high_24h: { usd: number };
        low_24h: { usd: number };
        price_change_percentage_24h: number;
        price_change_percentage_7d: number;
        price_change_percentage_30d: number;
        circulating_supply: number;
        total_supply: number;
        max_supply: number;
        ath: { usd: number };
        ath_change_percentage: { usd: number };
        ath_date: { usd: string };
        atl: { usd: number };
        atl_date: { usd: string };
    };
    genesis_date: string;
    categories: string[];
}

async function getCoinDetail(id: string): Promise<CryptoResult> {
    const result = await fetchJson<CoinDetail>(
        `/coins/${id}?localization=false&tickers=false&community_data=false&developer_data=false`,
    );

    if (!result.success) return result;

    const coin = result.data!;
    const md = coin.market_data;

    return {
        success: true,
        data: {
            id: coin.id,
            symbol: coin.symbol.toUpperCase(),
            name: coin.name,
            rank: coin.market_cap_rank,
            description: coin.description.en?.slice(0, 500),
            website: coin.links.homepage[0],
            categories: coin.categories.slice(0, 5),
            genesisDate: coin.genesis_date,
            price: {
                current: md.current_price.usd,
                high24h: md.high_24h.usd,
                low24h: md.low_24h.usd,
                change24h: md.price_change_percentage_24h?.toFixed(2) + '%',
                change7d: md.price_change_percentage_7d?.toFixed(2) + '%',
                change30d: md.price_change_percentage_30d?.toFixed(2) + '%',
            },
            market: {
                marketCap: md.market_cap.usd,
                volume24h: md.total_volume.usd,
                circulatingSupply: md.circulating_supply,
                totalSupply: md.total_supply,
                maxSupply: md.max_supply,
            },
            ath: {
                price: md.ath.usd,
                changeFromAth: md.ath_change_percentage.usd?.toFixed(2) + '%',
                date: md.ath_date.usd,
            },
            atl: {
                price: md.atl.usd,
                date: md.atl_date.usd,
            },
            timestamp: new Date().toISOString(),
        },
    };
}

interface ChartData {
    prices: [number, number][];
}

async function getHistory(id: string, days: number): Promise<CryptoResult> {
    const result = await fetchJson<ChartData>(
        `/coins/${id}/market_chart?vs_currency=usd&days=${days}`,
    );

    if (!result.success) return result;

    const prices = result.data!.prices.map(([timestamp, price]) => ({
        date: new Date(timestamp).toISOString().split('T')[0],
        price: price,
    }));

    // Calculate stats
    const priceValues = prices.map((p) => p.price);
    const firstPrice = priceValues[0];
    const lastPrice = priceValues[priceValues.length - 1];
    const change = lastPrice && firstPrice ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0;

    return {
        success: true,
        data: {
            id,
            days,
            dataPoints: prices.length,
            summary: {
                startPrice: firstPrice?.toFixed(2),
                endPrice: lastPrice?.toFixed(2),
                change: change.toFixed(2) + '%',
                high: Math.max(...priceValues).toFixed(2),
                low: Math.min(...priceValues).toFixed(2),
            },
            prices: prices.slice(-30), // Last 30 points to avoid too much data
        },
    };
}

interface GlobalData {
    data: {
        active_cryptocurrencies: number;
        markets: number;
        total_market_cap: { usd: number };
        total_volume: { usd: number };
        market_cap_percentage: { btc: number; eth: number };
        market_cap_change_percentage_24h_usd: number;
    };
}

async function getGlobalStats(): Promise<CryptoResult> {
    const result = await fetchJson<GlobalData>('/global');

    if (!result.success) return result;

    const d = result.data!.data;

    return {
        success: true,
        data: {
            activeCryptos: d.active_cryptocurrencies,
            markets: d.markets,
            totalMarketCap: d.total_market_cap.usd,
            totalVolume24h: d.total_volume.usd,
            marketCapChange24h: d.market_cap_change_percentage_24h_usd?.toFixed(2) + '%',
            dominance: {
                btc: d.market_cap_percentage.btc?.toFixed(2) + '%',
                eth: d.market_cap_percentage.eth?.toFixed(2) + '%',
            },
            timestamp: new Date().toISOString(),
        },
    };
}

export function createCryptoMcpServer() {
    const server = new McpServer({
        name: 'crypto-server',
        version: '1.0.0',
    });

    server.registerTool(
        'crypto_price',
        {
            title: 'Crypto Price',
            description:
                'Get current price for one or more cryptocurrencies. Use coin IDs like "bitcoin", "ethereum", "solana".',
            inputSchema: {
                ids: z
                    .array(z.string())
                    .describe("Coin IDs (e.g., ['bitcoin', 'ethereum', 'solana'])"),
            },
        },
        async ({ ids }) => {
            const result = await getPrice(ids.map((id) => id.toLowerCase()));
            return formatResult(result);
        },
    );

    server.registerTool(
        'crypto_markets',
        {
            title: 'Top Cryptocurrencies',
            description:
                'Get top cryptocurrencies by market cap with price, volume, and 24h change.',
            inputSchema: {
                limit: z.number().default(20).describe('Number of coins (default: 20, max: 100)'),
            },
        },
        async ({ limit }) => {
            const result = await getMarkets(Math.min(limit, 100));
            return formatResult(result);
        },
    );

    server.registerTool(
        'crypto_search',
        {
            title: 'Search Crypto',
            description:
                'Search for cryptocurrencies by name or symbol. Returns coin IDs for other tools.',
            inputSchema: {
                query: z.string().describe("Search term (e.g., 'bitcoin', 'eth', 'solana')"),
            },
        },
        async ({ query }) => {
            const result = await searchCoins(query);
            return formatResult(result);
        },
    );

    server.registerTool(
        'crypto_trending',
        {
            title: 'Trending Crypto',
            description: 'Get currently trending cryptocurrencies based on search popularity.',
            inputSchema: {},
        },
        async () => {
            const result = await getTrending();
            return formatResult(result);
        },
    );

    server.registerTool(
        'crypto_detail',
        {
            title: 'Crypto Details',
            description:
                'Get detailed info for a cryptocurrency: description, market data, ATH/ATL, supply.',
            inputSchema: {
                id: z
                    .string()
                    .describe(
                        "Coin ID (e.g., 'bitcoin', 'ethereum'). Use crypto_search to find IDs.",
                    ),
            },
        },
        async ({ id }) => {
            const result = await getCoinDetail(id.toLowerCase());
            return formatResult(result);
        },
    );

    server.registerTool(
        'crypto_history',
        {
            title: 'Crypto History',
            description: 'Get historical price data for a cryptocurrency.',
            inputSchema: {
                id: z.string().describe("Coin ID (e.g., 'bitcoin')"),
                days: z
                    .enum(['1', '7', '30', '90', '365'])
                    .default('30')
                    .describe('Number of days (default: 30)'),
            },
        },
        async ({ id, days }) => {
            const result = await getHistory(id.toLowerCase(), parseInt(days));
            return formatResult(result);
        },
    );

    server.registerTool(
        'crypto_global',
        {
            title: 'Global Crypto Stats',
            description:
                'Get global cryptocurrency market statistics: total market cap, volume, BTC dominance.',
            inputSchema: {},
        },
        async () => {
            const result = await getGlobalStats();
            return formatResult(result);
        },
    );

    return server;
}

async function main() {
    const server = createCryptoMcpServer();

    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('[MCP] Crypto started');
}

// Run if executed directly
const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
    main().catch((error) => {
        console.error('[MCP Crypto Server] Fatal error:', error);
        process.exit(1);
    });
}

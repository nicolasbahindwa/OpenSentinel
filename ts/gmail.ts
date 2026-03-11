// MCP Gmail Server
// Email tools: list, search, send, draft, read, delete

import { loadEnv } from '@flopsy/shared';
loadEnv();

import { getGoogleAuthPaths } from './google-auth-helper';

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { google, type gmail_v1 } from 'googleapis';
import { z } from 'zod';
import fs from 'fs/promises';
import path from 'path';

import http from 'http';
import { execFile } from 'child_process';
import { URL } from 'url';

const SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send',
];

interface Credentials {
    installed?: { client_id: string; client_secret: string; redirect_uris: string[] };
    web?: { client_id: string; client_secret: string; redirect_uris: string[] };
}

interface TokenData {
    access_token: string;
    refresh_token: string;
    expiry_date: number;
}

/**
 * Open URL in default browser (safe - no shell injection)
 */
function openBrowser(url: string): void {
    const platform = process.platform;
    if (platform === 'darwin') {
        execFile('open', [url]);
    } else if (platform === 'win32') {
        execFile('cmd', ['/c', 'start', '', url]);
    } else {
        execFile('xdg-open', [url]);
    }
}

/**
 * Run local OAuth flow - opens browser for consent
 */
async function runLocalAuthFlow(
    oAuth2Client: InstanceType<typeof google.auth.OAuth2>,
    scopes: string[],
): Promise<TokenData> {
    return new Promise((resolve, reject) => {
        const server = http.createServer();
        server.listen(0, '127.0.0.1', () => {
            const address = server.address();
            const port = typeof address === 'object' && address ? address.port : 3000;
            const redirectUri = `http://127.0.0.1:${port}`;

            const authUrl = oAuth2Client.generateAuthUrl({
                access_type: 'offline',
                scope: scopes,
                prompt: 'consent',
                redirect_uri: redirectUri,
            });

            console.error(`\n[Gmail MCP] Opening browser for authentication...`);
            console.error(`[Gmail MCP] If browser doesn't open, visit:\n${authUrl}\n`);

            openBrowser(authUrl);

            server.on('request', async (req, res) => {
                console.error(`[Gmail MCP] Received callback: ${req.url}`);
                try {
                    const url = new URL(req.url ?? '', redirectUri);
                    const code = url.searchParams.get('code');
                    const error = url.searchParams.get('error');

                    if (error) {
                        console.error(`[Gmail MCP] OAuth error: ${error}`);
                        res.writeHead(400, { 'Content-Type': 'text/html' });
                        res.end(`<h1>Authentication failed</h1><p>${error}</p>`);
                        server.close();
                        reject(new Error(`OAuth error: ${error}`));
                        return;
                    }

                    if (code) {
                        console.error(
                            '[Gmail MCP] Got authorization code, exchanging for token...',
                        );
                        const { tokens } = await oAuth2Client.getToken({
                            code,
                            redirect_uri: redirectUri,
                        });
                        console.error('[Gmail MCP] Token received successfully');
                        oAuth2Client.setCredentials(tokens);

                        res.writeHead(200, { 'Content-Type': 'text/html' });
                        res.end(
                            '<h1>Authentication successful!</h1><p>You can close this window.</p>',
                        );

                        server.close();
                        resolve(tokens as TokenData);
                    } else {
                        console.error('[Gmail MCP] No code in callback');
                        res.writeHead(400, { 'Content-Type': 'text/html' });
                        res.end('<h1>Authentication failed</h1><p>No code received.</p>');
                    }
                } catch (error) {
                    console.error('[Gmail MCP] Token exchange error:', error);
                    res.writeHead(500, { 'Content-Type': 'text/html' });
                    res.end(`<h1>Authentication failed</h1><p>${error}</p>`);
                    server.close();
                    reject(error);
                }
            });
        });

        server.on('error', reject);
    });
}

async function createAuthClient(credentialsPath: string, tokenPath: string) {
    const credContent = await fs.readFile(credentialsPath, 'utf-8');
    const credentials: Credentials = JSON.parse(credContent);
    const { client_id, client_secret, redirect_uris } =
        credentials.installed ?? credentials.web ?? {};

    if (!client_id || !client_secret) {
        throw new Error('Invalid credentials file');
    }

    const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris?.[0]);

    // Try to load existing token
    let token: TokenData | null = null;
    try {
        const tokenContent = await fs.readFile(tokenPath, 'utf-8');
        token = JSON.parse(tokenContent);
    } catch {
        // Token file doesn't exist
    }

    // Set up automatic token refresh listener
    oAuth2Client.on('tokens', async (tokens) => {
        try {
            let existingToken: TokenData | null = null;
            try {
                const content = await fs.readFile(tokenPath, 'utf-8');
                existingToken = JSON.parse(content);
            } catch {
                // No existing token
            }
            const updatedToken = { ...existingToken, ...tokens };
            await fs.mkdir(path.dirname(tokenPath), { recursive: true });
            await fs.writeFile(tokenPath, JSON.stringify(updatedToken, null, 2));
            console.error('[Gmail MCP] Token auto-refreshed and saved');
        } catch (error) {
            console.error('[Gmail MCP] Failed to save refreshed token:', error);
        }
    });

    if (token) {
        oAuth2Client.setCredentials(token);

        // Refresh if expired or expiring soon (within 5 minutes)
        const expiryBuffer = 5 * 60 * 1000;
        if (token.expiry_date && token.expiry_date < Date.now() + expiryBuffer) {
            console.error('[Gmail MCP] Token expired or expiring soon, refreshing...');
            try {
                const { credentials: newCreds } = await oAuth2Client.refreshAccessToken();
                oAuth2Client.setCredentials(newCreds);
            } catch (error) {
                console.error('[Gmail MCP] Token refresh failed, re-authenticating...');
                const newToken = await runLocalAuthFlow(oAuth2Client, SCOPES);
                await fs.mkdir(path.dirname(tokenPath), { recursive: true });
                await fs.writeFile(tokenPath, JSON.stringify(newToken, null, 2));
            }
        }
    } else {
        // No token - run OAuth flow
        console.error('[Gmail MCP] No token found, starting authentication...');
        const newToken = await runLocalAuthFlow(oAuth2Client, SCOPES);
        console.error('[Gmail MCP] OAuth flow completed, saving token...');

        // Ensure directory exists before saving token
        const tokenDir = path.dirname(tokenPath);
        console.error(`[Gmail MCP] Creating directory: ${tokenDir}`);
        await fs.mkdir(tokenDir, { recursive: true });

        console.error(`[Gmail MCP] Writing token to: ${tokenPath}`);
        await fs.writeFile(tokenPath, JSON.stringify(newToken, null, 2));
        console.error('[Gmail MCP] Token saved successfully!');
    }

    return oAuth2Client;
}

function extractBody(payload?: gmail_v1.Schema$MessagePart): string {
    if (!payload) return '';

    if (payload.body?.data) {
        return Buffer.from(payload.body.data, 'base64').toString('utf-8');
    }

    if (payload.parts) {
        for (const part of payload.parts) {
            if (part.mimeType === 'text/plain' || part.mimeType === 'text/html') {
                if (part.body?.data) {
                    return Buffer.from(part.body.data, 'base64').toString('utf-8');
                }
            }
            const nested = extractBody(part);
            if (nested) return nested;
        }
    }

    return '';
}

function parseEmail(message: gmail_v1.Schema$Message) {
    const headers = message.payload?.headers ?? [];
    const getHeader = (name: string) =>
        headers.find((h) => h.name?.toLowerCase() === name.toLowerCase())?.value ?? '';

    return {
        id: message.id ?? '',
        threadId: message.threadId ?? '',
        subject: getHeader('subject'),
        from: getHeader('from'),
        to: getHeader('to'),
        date: getHeader('date'),
        body: extractBody(message.payload),
        snippet: message.snippet ?? '',
    };
}

export async function createGmailMcpServer(credentialsPath: string, tokenPath: string) {
    const auth = await createAuthClient(credentialsPath, tokenPath);
    const gmail = (google.gmail as any)({ version: 'v1', auth });

    const server = new McpServer({
        name: 'gmail-server',
        version: '1.0.0',
    });

    server.registerTool(
        'gmail_list',
        {
            title: 'List Emails',
            description: 'List emails from inbox with optional filtering',
            inputSchema: {
                maxResults: z.number().default(20).describe('Maximum emails to return'),
                query: z.string().optional().describe('Gmail search query'),
                unreadOnly: z.boolean().default(false).describe('Only show unread'),
            },
        },
        async ({ maxResults, query, unreadOnly }) => {
            const labelIds = unreadOnly ? ['INBOX', 'UNREAD'] : ['INBOX'];

            const listParams: gmail_v1.Params$Resource$Users$Messages$List = {
                userId: 'me',
                maxResults,
                labelIds,
            };
            if (query) listParams.q = query;

            const res = await gmail.users.messages.list(listParams);
            const messages = res.data.messages ?? [];

            const emails = [];
            for (const msg of messages.slice(0, maxResults)) {
                if (!msg.id) continue;
                const full = await gmail.users.messages.get({
                    userId: 'me',
                    id: msg.id,
                    format: 'full',
                });
                emails.push(parseEmail(full.data));
            }

            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify(
                            { success: true, count: emails.length, emails },
                            null,
                            2,
                        ),
                    },
                ],
            };
        },
    );

    server.registerTool(
        'gmail_search',
        {
            title: 'Search Emails',
            description: 'Search emails using Gmail query syntax',
            inputSchema: {
                query: z.string().describe("Search query (e.g., 'from:boss subject:urgent')"),
                maxResults: z.number().default(20).describe('Maximum results'),
            },
        },
        async ({ query, maxResults }) => {
            const res = await gmail.users.messages.list({ userId: 'me', q: query, maxResults });
            const messages = res.data.messages ?? [];

            const emails = [];
            for (const msg of messages) {
                if (!msg.id) continue;
                const full = await gmail.users.messages.get({
                    userId: 'me',
                    id: msg.id,
                    format: 'full',
                });
                emails.push(parseEmail(full.data));
            }

            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify(
                            { success: true, count: emails.length, query, emails },
                            null,
                            2,
                        ),
                    },
                ],
            };
        },
    );

    server.registerTool(
        'gmail_get',
        {
            title: 'Get Email',
            description: 'Get full content of a specific email',
            inputSchema: {
                messageId: z.string().describe('Gmail message ID'),
            },
        },
        async ({ messageId }) => {
            const res = await gmail.users.messages.get({
                userId: 'me',
                id: messageId,
                format: 'full',
            });
            const email = parseEmail(res.data);

            return {
                content: [
                    { type: 'text', text: JSON.stringify({ success: true, email }, null, 2) },
                ],
            };
        },
    );

    server.registerTool(
        'gmail_send',
        {
            title: 'Send Email',
            description: 'Send an email',
            inputSchema: {
                to: z.string().describe('Recipient email'),
                subject: z.string().describe('Email subject'),
                body: z.string().describe('Email body (plain text)'),
                cc: z.string().optional().describe('CC recipients'),
                bcc: z.string().optional().describe('BCC recipients'),
            },
        },
        async ({ to, subject, body, cc, bcc }) => {
            const lines = [
                `To: ${to}`,
                `Subject: ${subject}`,
                `Content-Type: text/plain; charset="UTF-8"`,
            ];
            if (cc) lines.push(`Cc: ${cc}`);
            if (bcc) lines.push(`Bcc: ${bcc}`);
            lines.push('', body);

            const raw = Buffer.from(lines.join('\r\n')).toString('base64url');
            const res = await gmail.users.messages.send({ userId: 'me', requestBody: { raw } });

            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify({ success: true, messageId: res.data.id }, null, 2),
                    },
                ],
            };
        },
    );

    server.registerTool(
        'gmail_draft',
        {
            title: 'Create Draft',
            description: 'Create an email draft',
            inputSchema: {
                to: z.string().describe('Recipient email'),
                subject: z.string().describe('Email subject'),
                body: z.string().describe('Email body'),
            },
        },
        async ({ to, subject, body }) => {
            const lines = [
                `To: ${to}`,
                `Subject: ${subject}`,
                `Content-Type: text/plain; charset="UTF-8"`,
                '',
                body,
            ];
            const raw = Buffer.from(lines.join('\r\n')).toString('base64url');

            const res = await gmail.users.drafts.create({
                userId: 'me',
                requestBody: { message: { raw } },
            });

            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify({ success: true, draftId: res.data.id }, null, 2),
                    },
                ],
            };
        },
    );

    server.registerTool(
        'gmail_mark_read',
        {
            title: 'Mark as Read',
            description: 'Mark an email as read',
            inputSchema: {
                messageId: z.string().describe('Gmail message ID'),
            },
        },
        async ({ messageId }) => {
            await gmail.users.messages.modify({
                userId: 'me',
                id: messageId,
                requestBody: { removeLabelIds: ['UNREAD'] },
            });

            return {
                content: [{ type: 'text', text: JSON.stringify({ success: true, messageId }) }],
            };
        },
    );

    server.registerTool(
        'gmail_delete',
        {
            title: 'Delete Email',
            description: 'Move email to trash',
            inputSchema: {
                messageId: z.string().describe('Gmail message ID'),
            },
        },
        async ({ messageId }) => {
            await gmail.users.messages.trash({ userId: 'me', id: messageId });

            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify({ success: true, messageId, deleted: true }),
                    },
                ],
            };
        },
    );

    server.registerTool(
        'gmail_labels',
        {
            title: 'Get Labels',
            description: 'Get all Gmail labels',
            inputSchema: {},
        },
        async () => {
            const res = await gmail.users.labels.list({ userId: 'me' });
            const labels = (res.data.labels ?? []).map((l: any) => ({
                id: l.id,
                name: l.name,
                type: l.type,
            }));

            return {
                content: [
                    { type: 'text', text: JSON.stringify({ success: true, labels }, null, 2) },
                ],
            };
        },
    );

    server.registerResource(
        'gmail_profile',
        'gmail://profile',
        {
            title: 'Gmail Profile',
            description: "User's Gmail profile",
            mimeType: 'application/json',
        },
        async () => {
            const res = await gmail.users.getProfile({ userId: 'me' });
            return {
                contents: [
                    {
                        uri: 'gmail://profile',
                        mimeType: 'application/json',
                        text: JSON.stringify(
                            {
                                email: res.data.emailAddress,
                                messagesTotal: res.data.messagesTotal,
                                threadsTotal: res.data.threadsTotal,
                            },
                            null,
                            2,
                        ),
                    },
                ],
            };
        },
    );

    return server;
}

async function main() {
    try {
        const { credentialsPath, tokenPath } = getGoogleAuthPaths('gmail');
        const server = await createGmailMcpServer(credentialsPath, tokenPath);
        const transport = new StdioServerTransport();
        await server.connect(transport);
        console.error('[MCP] Gmail started');
    } catch (error) {
        console.error('[MCP] Gmail failed:', error);
        process.exit(1);
    }
}

const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
    main();
}

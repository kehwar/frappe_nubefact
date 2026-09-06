import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parseEnv } from "node:util";
import { StringEnum } from "@earendil-works/pi-ai";
import {
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    formatSize,
    getMarkdownTheme,
    truncateHead,
    type ExtensionAPI,
} from "@earendil-works/pi-coding-agent";
import { Markdown, Text } from "@earendil-works/pi-tui";
import { Type } from "typebox";
import {
    renderExecMarkdown,
    renderFetchMarkdown,
    responseFromToolContent,
    type FrappeExecDetails,
    type FrappeFetchDetails,
    type FrappeHttpMethod,
} from "./frappe/renderer.ts";

const CONFIG_KEYS = [
    "FRAPPE_PROD_URL",
    "FRAPPE_PROD_API_KEY",
    "FRAPPE_PROD_API_SECRET",
] as const;
const OUTPUT_NOTICE_BYTES = 1024;
const OUTPUT_NOTICE_LINES = 5;
const MAX_CAPTURE_BYTES = DEFAULT_MAX_BYTES + 1;
const DEFAULT_TIMEOUT_SECONDS = 30;
const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);
const HTTP_METHODS = [
    "GET",
    "POST",
    "PATCH",
    "DELETE",
] as const satisfies readonly FrappeHttpMethod[];

type ConfigKey = (typeof CONFIG_KEYS)[number];
type ProdConfig = Record<ConfigKey, string>;
type Query = Record<string, string> | undefined;
type HttpMethod = (typeof HTTP_METHODS)[number];

const fetchParameters = Type.Object({
    path: Type.String({
        description:
            "Frappe API path beginning with /api/, for example /api/resource/Item or /api/method/frappe.auth.get_logged_user. A query string may be included.",
    }),
    method: Type.Optional(StringEnum(HTTP_METHODS)),
    query: Type.Optional(
        Type.Record(Type.String(), Type.String(), {
            description:
                "Optional query parameters. Values must be strings; JSON-encode Frappe fields, filters, and similar structured values.",
        }),
    ),
    body: Type.Optional(
        Type.String({
            description:
                "JSON-encoded request body for POST, PATCH, or DELETE. Omit for GET and when the endpoint does not require a body.",
        }),
    ),
    timeoutSeconds: Type.Optional(
        Type.Integer({
            description: "Request timeout in seconds (default 30).",
            minimum: 1,
            maximum: 120,
        }),
    ),
});

const execParameters = Type.Object({
    code: Type.String({
        description:
            "Python code to run through Frappe System Console safe_exec (RestrictedPython). Use print() for output; imports and private attribute access are forbidden.",
    }),
    commit: Type.Optional(
        Type.Boolean({
            description:
                "Whether System Console should commit database changes after execution (default false). This cannot undo explicit commits or external side effects performed by the code.",
        }),
    ),
    timeoutSeconds: Type.Optional(
        Type.Integer({
            description: "Request timeout in seconds (default 30).",
            minimum: 1,
            maximum: 120,
        }),
    ),
});

async function loadConfig(cwd: string): Promise<ProdConfig> {
    let fileValues: Record<string, string> = {};
    const envPath = join(cwd, ".env");

    try {
        fileValues = parseEnv(await readFile(envPath, "utf8"));
    } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
            throw new Error(
                `Could not parse ${envPath}: ${errorMessage(error)}`,
            );
        }
    }

    const values = Object.fromEntries(
        CONFIG_KEYS.map((key) => [
            key,
            (process.env[key] ?? fileValues[key] ?? "").trim(),
        ]),
    ) as ProdConfig;
    const missing = CONFIG_KEYS.filter((key) => !values[key]);

    if (missing.length > 0) {
        throw new Error(
            `Missing ${missing.join(", ")}. Copy .env.example to .env and configure a least-privileged Frappe API user.`,
        );
    }

    if (values.FRAPPE_PROD_API_KEY.includes(":")) {
        throw new Error("FRAPPE_PROD_API_KEY cannot contain a colon.");
    }
    if (values.FRAPPE_PROD_API_SECRET.includes(":")) {
        throw new Error("FRAPPE_PROD_API_SECRET cannot contain a colon.");
    }

    return values;
}

function buildApiUrl(siteUrl: string, path: string, query: Query): URL {
    let base: URL;
    try {
        base = new URL(siteUrl);
    } catch {
        throw new Error("FRAPPE_PROD_URL must be a valid absolute URL.");
    }

    if (!["http:", "https:"].includes(base.protocol)) {
        throw new Error(
            "FRAPPE_PROD_URL must use HTTPS (or HTTP for loopback testing).",
        );
    }
    if (base.protocol === "http:" && !LOOPBACK_HOSTS.has(base.hostname)) {
        throw new Error(
            "FRAPPE_PROD_URL must use HTTPS for a non-loopback site.",
        );
    }
    if (base.username || base.password || base.search || base.hash) {
        throw new Error(
            "FRAPPE_PROD_URL must not contain credentials, a query string, or a fragment.",
        );
    }
    if (!path.startsWith("/api/") && path !== "/api") {
        throw new Error(
            "path must begin with /api/ so credentials cannot be sent to a non-API route.",
        );
    }
    if (path.includes("\r") || path.includes("\n")) {
        throw new Error("path cannot contain line breaks.");
    }

    base.pathname = `${base.pathname.replace(/\/+$/, "")}/`;
    const url = new URL(path.replace(/^\/+/, ""), base);
    const apiPrefix = `${base.pathname.replace(/\/+$/, "")}/api`;

    if (
        url.origin !== base.origin ||
        (url.pathname !== apiPrefix &&
            !url.pathname.startsWith(`${apiPrefix}/`))
    ) {
        throw new Error(
            "path must resolve inside the configured site's /api route.",
        );
    }

    for (const [key, value] of Object.entries(query ?? {})) {
        url.searchParams.set(key, value);
    }

    return url;
}

async function readBoundedText(
    response: Response,
): Promise<{ text: string; limited: boolean }> {
    if (!response.body) return { text: "", limited: false };

    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let capturedBytes = 0;
    let limited = false;

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const remaining = MAX_CAPTURE_BYTES - capturedBytes;
            if (value.byteLength > remaining) {
                if (remaining > 0) chunks.push(value.subarray(0, remaining));
                limited = true;
                await reader.cancel();
                break;
            }

            chunks.push(value);
            capturedBytes += value.byteLength;
        }
    } finally {
        reader.releaseLock();
    }

    return {
        text: Buffer.concat(chunks.map((chunk) => Buffer.from(chunk))).toString(
            "utf8",
        ),
        limited,
    };
}

function prepareRequestBody(
    method: HttpMethod,
    body: string | undefined,
): string | undefined {
    if (body === undefined) return undefined;
    if (method === "GET") {
        throw new Error("body is not allowed for GET requests.");
    }

    try {
        return JSON.stringify(JSON.parse(body));
    } catch (error) {
        throw new Error(`body must be valid JSON: ${errorMessage(error)}`);
    }
}

function formatBody(body: string, contentType: string): string {
    if (!body) return "(empty response body)";
    if (!contentType.toLowerCase().includes("json")) return body;

    try {
        return JSON.stringify(JSON.parse(body), null, 2);
    } catch {
        return body;
    }
}

function countFrappeRecords(body: string): number | undefined {
    try {
        const payload = JSON.parse(body) as unknown;
        if (Array.isArray(payload)) return payload.length;
        if (!isRecord(payload)) return undefined;
        if (Array.isArray(payload.data)) return payload.data.length;
        if ("data" in payload) return payload.data === null ? 0 : 1;
        if (Array.isArray(payload.message)) return payload.message.length;
        if ("message" in payload) return payload.message === null ? 0 : 1;
        return undefined;
    } catch {
        return undefined;
    }
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function formatOutput(
    method: HttpMethod,
    response: Response,
    body: string,
    bodyLimited: boolean,
) {
    const contentType = response.headers.get("content-type") ?? "unknown";
    const fullOutput = [
        `${method} ${response.url}`,
        `HTTP ${response.status} ${response.statusText}`.trimEnd(),
        `Content-Type: ${contentType}`,
        "",
        formatBody(body, contentType),
    ].join("\n");
    const truncation = truncateHead(fullOutput, {
        maxBytes: DEFAULT_MAX_BYTES - OUTPUT_NOTICE_BYTES,
        maxLines: DEFAULT_MAX_LINES - OUTPUT_NOTICE_LINES,
    });
    const truncated = bodyLimited || truncation.truncated;
    let text = truncation.content;

    if (truncated) {
        text += `\n\n[Production response truncated to at most ${DEFAULT_MAX_LINES} lines or ${formatSize(DEFAULT_MAX_BYTES)} and not saved to disk. Request a narrower result.]`;
    }

    return { text, contentType, truncated };
}

function formatExecOutput(
    response: Response,
    body: string,
    bodyLimited: boolean,
): {
    text: string;
    committed: boolean;
    traceback: boolean;
    truncated: boolean;
} {
    if (bodyLimited) {
        const output = formatOutput("POST", response, body, true);
        return {
            text: output.text,
            committed: false,
            traceback: false,
            truncated: true,
        };
    }

    let payload: unknown;
    try {
        payload = JSON.parse(body);
    } catch {
        const output = formatOutput("POST", response, body, false);
        return {
            text: output.text,
            committed: false,
            traceback: false,
            truncated: output.truncated,
        };
    }

    const message = (payload as { message?: unknown }).message;
    if (!message || typeof message !== "object") {
        const output = formatOutput("POST", response, body, false);
        return {
            text: output.text,
            committed: false,
            traceback: false,
            truncated: output.truncated,
        };
    }

    const result = message as { commit?: unknown; output?: unknown };
    const committed = Boolean(result.commit);
    const consoleOutput =
        typeof result.output === "string"
            ? result.output
            : "(execution completed without console output)";
    const traceback = consoleOutput.startsWith("Traceback");
    const fullOutput = [
        `Committed by System Console: ${committed ? "yes" : "no"}`,
        "",
        consoleOutput,
    ].join("\n");
    const truncation = truncateHead(fullOutput, {
        maxBytes: DEFAULT_MAX_BYTES - OUTPUT_NOTICE_BYTES,
        maxLines: DEFAULT_MAX_LINES - OUTPUT_NOTICE_LINES,
    });
    let text = truncation.content;

    if (truncation.truncated) {
        text += `\n\n[System Console output truncated to at most ${DEFAULT_MAX_LINES} lines or ${formatSize(DEFAULT_MAX_BYTES)} and not saved to disk. Request narrower output.]`;
    }

    return { text, committed, traceback, truncated: truncation.truncated };
}

function textContent(content: Array<{ text?: string; type: string }>): string {
    const first = content[0];
    return first?.type === "text" ? (first.text ?? "") : "";
}

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

export default function frappeExtension(pi: ExtensionAPI) {
    pi.registerTool({
        name: "frappe_fetch",
        label: "Frappe fetch",
        description:
            "Call the configured production Frappe /api endpoint using token authentication.",
        promptSnippet:
            "Call the configured live production Frappe /api endpoint with GET, POST, PATCH, or DELETE",
        promptGuidelines: [
            "Use frappe_fetch for authenticated requests to the configured live production Frappe site; use local tools for development data.",
            "Treat frappe_fetch POST, PATCH, and DELETE requests as production writes: use them only when the user explicitly requests the change and inspect the complete path, query, and body first.",
            "Although frappe_fetch GET requests are normally read-oriented, verify that an /api/method GET endpoint is side-effect-free before calling it.",
        ],
        parameters: fetchParameters,

        async execute(_toolCallId, params, signal, _onUpdate, ctx) {
            const config = await loadConfig(ctx.cwd);
            const url = buildApiUrl(
                config.FRAPPE_PROD_URL,
                params.path,
                params.query,
            );
            const method = params.method ?? "GET";
            const requestBody = prepareRequestBody(method, params.body);
            const timeoutSeconds =
                params.timeoutSeconds ?? DEFAULT_TIMEOUT_SECONDS;
            const timeoutSignal = AbortSignal.timeout(timeoutSeconds * 1000);
            const requestSignal = signal
                ? AbortSignal.any([signal, timeoutSignal])
                : timeoutSignal;
            const headers: Record<string, string> = {
                Accept: "application/json, text/plain;q=0.9, text/*;q=0.8",
                Authorization: `token ${config.FRAPPE_PROD_API_KEY}:${config.FRAPPE_PROD_API_SECRET}`,
            };
            if (requestBody !== undefined) {
                headers["Content-Type"] = "application/json";
            }
            let response: Response;

            try {
                response = await fetch(url, {
                    method,
                    headers,
                    body: requestBody,
                    redirect: "manual",
                    signal: requestSignal,
                });
            } catch (error) {
                if (signal?.aborted)
                    throw new Error("Production Frappe request cancelled.");
                if (timeoutSignal.aborted) {
                    throw new Error(
                        `Production Frappe request timed out after ${timeoutSeconds} seconds.`,
                    );
                }
                throw new Error(
                    `Production Frappe request failed: ${errorMessage(error)}`,
                );
            }

            if (response.status >= 300 && response.status < 400) {
                await response.body?.cancel();
                throw new Error(
                    `Production Frappe API returned redirect HTTP ${response.status}. Configure FRAPPE_PROD_URL with the canonical HTTPS site URL; redirects are not followed so the API token cannot leave the configured origin.`,
                );
            }

            const contentType =
                response.headers.get("content-type")?.toLowerCase() ?? "";
            if (
                contentType &&
                !contentType.includes("json") &&
                !contentType.startsWith("text/") &&
                !contentType.includes("xml")
            ) {
                await response.body?.cancel();
                throw new Error(
                    `Production Frappe API returned unsupported Content-Type ${contentType}; this tool only returns JSON or text.`,
                );
            }

            const { text: body, limited: bodyLimited } =
                await readBoundedText(response);
            const output = formatOutput(method, response, body, bodyLimited);

            if (!response.ok) {
                throw new Error(
                    `Production Frappe API request failed:\n${output.text}`,
                );
            }

            return {
                content: [{ type: "text", text: output.text }],
                details: {
                    method,
                    url: response.url,
                    status: response.status,
                    statusText: response.statusText,
                    contentType: output.contentType,
                    recordCount: countFrappeRecords(body),
                    truncated: output.truncated,
                } satisfies FrappeFetchDetails,
            };
        },
        renderCall() {
            return new Text("", 0, 0);
        },
        renderResult(result, { expanded, isPartial }, _theme, context) {
            const method = context.args.method ?? "GET";
            if (isPartial) {
                return new Markdown(
                    "**Frappe API ▲**\n\nLoading…",
                    0,
                    0,
                    getMarkdownTheme(),
                );
            }
            if (context.isError) {
                return new Markdown(
                    renderFetchMarkdown({
                        body: context.args.body,
                        expanded,
                        isError: true,
                        method,
                        path: context.args.path,
                        query: context.args.query,
                        response: expanded
                            ? textContent(result.content)
                            : undefined,
                    }),
                    0,
                    0,
                    getMarkdownTheme(),
                );
            }

            const details = result.details as FrappeFetchDetails;
            return new Markdown(
                renderFetchMarkdown({
                    body: context.args.body,
                    contentType: details.contentType,
                    expanded,
                    method,
                    path: context.args.path,
                    query: context.args.query,
                    recordCount: details.recordCount,
                    response: responseFromToolContent(
                        textContent(result.content),
                    ),
                    status: details.status,
                    truncated: details.truncated,
                }),
                0,
                0,
                getMarkdownTheme(),
            );
        },
    });

    pi.registerTool({
        name: "frappe_exec",
        label: "Frappe RestrictedPython execution",
        description:
            "Run RestrictedPython on production through Frappe System Console.",
        promptSnippet:
            "Execute RestrictedPython through the configured live production Frappe System Console",
        promptGuidelines: [
            "Use frappe_exec only when the user explicitly requests execution against the live production Frappe site; prefer frappe_fetch for reads that the Frappe API can express.",
            "Treat every frappe_exec call as production write-capable: inspect the complete code before calling it, default commit to false, and set commit true only when the user explicitly requests persistent changes.",
            "Code passed to frappe_exec runs under Frappe RestrictedPython without imports; use print() for output and the preloaded frappe namespace for Frappe operations.",
        ],
        parameters: execParameters,

        async execute(_toolCallId, params, signal, _onUpdate, ctx) {
            const config = await loadConfig(ctx.cwd);
            const url = buildApiUrl(
                config.FRAPPE_PROD_URL,
                "/api/method/frappe.desk.doctype.system_console.system_console.execute_code",
                undefined,
            );
            const timeoutSeconds =
                params.timeoutSeconds ?? DEFAULT_TIMEOUT_SECONDS;
            const timeoutSignal = AbortSignal.timeout(timeoutSeconds * 1000);
            const requestSignal = signal
                ? AbortSignal.any([signal, timeoutSignal])
                : timeoutSignal;
            const doc = JSON.stringify({
                doctype: "System Console",
                type: "Python",
                console: params.code,
                commit: params.commit ? 1 : 0,
            });
            let response: Response;

            try {
                response = await fetch(url, {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                        Authorization: `token ${config.FRAPPE_PROD_API_KEY}:${config.FRAPPE_PROD_API_SECRET}`,
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ doc }),
                    redirect: "manual",
                    signal: requestSignal,
                });
            } catch (error) {
                if (signal?.aborted)
                    throw new Error("Production Frappe execution cancelled.");
                if (timeoutSignal.aborted) {
                    throw new Error(
                        `Production Frappe execution timed out after ${timeoutSeconds} seconds. The server may continue executing after the client disconnects.`,
                    );
                }
                throw new Error(
                    `Production Frappe execution request failed: ${errorMessage(error)}`,
                );
            }

            if (response.status >= 300 && response.status < 400) {
                await response.body?.cancel();
                throw new Error(
                    `Production Frappe System Console returned redirect HTTP ${response.status}. Configure FRAPPE_PROD_URL with the canonical HTTPS site URL; redirects are not followed so the API token cannot leave the configured origin.`,
                );
            }

            const contentType =
                response.headers.get("content-type")?.toLowerCase() ?? "";
            if (contentType && !contentType.includes("json")) {
                await response.body?.cancel();
                throw new Error(
                    `Production Frappe System Console returned unsupported Content-Type ${contentType}; JSON was expected.`,
                );
            }

            const { text: body, limited: bodyLimited } =
                await readBoundedText(response);
            if (!response.ok) {
                const output = formatOutput(
                    "POST",
                    response,
                    body,
                    bodyLimited,
                );
                throw new Error(
                    `Production Frappe execution request failed:\n${output.text}`,
                );
            }

            const output = formatExecOutput(response, body, bodyLimited);
            if (output.traceback) {
                throw new Error(
                    `Production Frappe RestrictedPython execution failed:\n${output.text}`,
                );
            }

            return {
                content: [{ type: "text", text: output.text }],
                details: {
                    method: "POST",
                    url: response.url,
                    status: response.status,
                    statusText: response.statusText,
                    contentType:
                        response.headers.get("content-type") ?? "unknown",
                    truncated: output.truncated,
                    committed: output.committed,
                } satisfies FrappeExecDetails,
            };
        },
        renderCall() {
            return new Text("", 0, 0);
        },
        renderResult(result, { expanded, isPartial }, _theme, context) {
            if (isPartial) {
                return new Markdown(
                    "**Frappe Exec ▲**\n\nLoading…",
                    0,
                    0,
                    getMarkdownTheme(),
                );
            }
            if (context.isError) {
                return new Markdown(
                    renderExecMarkdown({
                        code: context.args.code,
                        expanded,
                        isError: true,
                        response: expanded
                            ? textContent(result.content)
                            : undefined,
                    }),
                    0,
                    0,
                    getMarkdownTheme(),
                );
            }

            const details = result.details as FrappeExecDetails;
            return new Markdown(
                renderExecMarkdown({
                    code: context.args.code,
                    committed: details.committed,
                    expanded,
                    response: responseFromToolContent(
                        textContent(result.content),
                    ),
                    truncated: details.truncated,
                }),
                0,
                0,
                getMarkdownTheme(),
            );
        },
    });
}

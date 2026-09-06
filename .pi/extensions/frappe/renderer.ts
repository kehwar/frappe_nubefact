const COMPACT_REQUEST_LENGTH = 160;

export type FrappeHttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface FrappeFetchDetails {
    method: FrappeHttpMethod;
    url: string;
    status: number;
    statusText: string;
    contentType: string;
    recordCount: number | undefined;
    truncated: boolean;
}

export interface FrappeExecDetails {
    method: "POST";
    url: string;
    status: number;
    statusText: string;
    contentType: string;
    truncated: boolean;
    committed: boolean;
}

type FetchMarkdownOptions = {
    body?: string;
    contentType?: string;
    expanded: boolean;
    isError?: boolean;
    method: FrappeHttpMethod;
    path: string;
    query?: Record<string, string>;
    recordCount?: number;
    response?: string;
    status?: number;
    truncated?: boolean;
};

type ExecMarkdownOptions = {
    code: string;
    committed?: boolean;
    expanded: boolean;
    isError?: boolean;
    response?: string;
    truncated?: boolean;
};

export function renderFetchMarkdown(options: FetchMarkdownOptions): string {
    const request = fetchRequest(options);
    const sections = [
        title("Frappe API ▲", fetchFacts(options)),
        fencedCode(
            "text",
            options.expanded ? request : truncateRequest(request),
        ),
    ];

    if (options.expanded && options.body !== undefined) {
        sections.push(fencedCode("json", formatJson(options.body)));
    }
    if (options.expanded && options.response !== undefined) {
        sections.push(
            fencedCode(responseLanguage(options.contentType), options.response),
        );
    }

    return sections.join("\n\n");
}

export function renderExecMarkdown(options: ExecMarkdownOptions): string {
    const sections = [
        title("Frappe Exec ▲", execFacts(options)),
        fencedCode(
            "python",
            options.expanded
                ? options.code
                : truncateRequest(compactCode(options.code)),
        ),
    ];

    if (options.expanded && options.response !== undefined) {
        sections.push(fencedCode("text", options.response));
    }

    return sections.join("\n\n");
}

export function responseFromToolContent(content: string): string {
    const separator = content.indexOf("\n\n");
    return separator === -1 ? content : content.slice(separator + 2);
}

function fetchRequest(options: FetchMarkdownOptions): string {
    const parameters = new URLSearchParams(options.query ?? {}).toString();
    const separator = options.path.includes("?") ? "&" : "?";
    const path = parameters
        ? `${options.path}${separator}${parameters}`
        : options.path;
    return `${options.method} ${path}`;
}

function fetchFacts(options: FetchMarkdownOptions): string[] {
    if (options.isError) return ["failed"];

    const facts: string[] = [];
    if (options.status !== undefined) facts.push(`HTTP ${options.status}`);
    if (options.recordCount !== undefined) {
        facts.push(
            `${options.recordCount} record${options.recordCount === 1 ? "" : "s"}`,
        );
    }
    if (options.truncated) facts.push("truncated");
    return facts;
}

function execFacts(options: ExecMarkdownOptions): string[] {
    if (options.isError) return ["failed"];

    const facts = [options.committed ? "committed" : "rolled back"];
    if (options.truncated) facts.push("truncated");
    return facts;
}

function compactCode(code: string): string {
    return code.replace(/\s*\n\s*/gu, " ").trim();
}

function formatJson(value: string): string {
    try {
        return JSON.stringify(JSON.parse(value), null, 2);
    } catch {
        return value;
    }
}

function responseLanguage(contentType: string | undefined): string {
    const normalized = contentType?.toLowerCase() ?? "";
    if (normalized.includes("json")) return "json";
    if (normalized.includes("xml")) return "xml";
    return "text";
}

function title(tool: string, facts: string[]): string {
    return facts.length === 0
        ? `**${tool}**`
        : `**${tool} (${facts.join(", ")})**`;
}

function fencedCode(language: string, content: string): string {
    const fence = "`".repeat(Math.max(3, longestBacktickRun(content) + 1));
    return `${fence}${language}\n${content}\n${fence}`;
}

function longestBacktickRun(content: string): number {
    return Math.max(
        0,
        ...[...content.matchAll(/`+/gu)].map((match) => match[0].length),
    );
}

function truncateRequest(request: string): string {
    if (request.length <= COMPACT_REQUEST_LENGTH) return request;
    return `${request.slice(0, COMPACT_REQUEST_LENGTH - 1)}…`;
}

import assert from "node:assert/strict";
import { test } from "node:test";
import {
    renderExecMarkdown,
    renderFetchMarkdown,
    responseFromToolContent,
} from "./renderer.ts";

test("renders a compact Frappe API request with status and record count", () => {
    const markdown = renderFetchMarkdown({
        expanded: false,
        method: "GET",
        path: "/api/resource/Item",
        query: { limit_page_length: "2" },
        recordCount: 2,
        status: 200,
    });

    assert.equal(
        markdown,
        [
            "**Frappe API ▲ (HTTP 200, 2 records)**",
            "",
            "```text",
            "GET /api/resource/Item?limit_page_length=2",
            "```",
        ].join("\n"),
    );
});

test("renders an expanded write request with its JSON body and response", () => {
    const markdown = renderFetchMarkdown({
        body: '{"description":"Created"}',
        contentType: "application/json",
        expanded: true,
        method: "POST",
        path: "/api/resource/ToDo",
        response: '{\n  "data": {\n    "name": "TODO-1"\n  }\n}',
        status: 200,
    });

    assert.equal(
        markdown,
        [
            "**Frappe API ▲ (HTTP 200)**",
            "",
            "```text",
            "POST /api/resource/ToDo",
            "```",
            "",
            "```json",
            "{",
            '  "description": "Created"',
            "}",
            "```",
            "",
            "```json",
            "{",
            '  "data": {',
            '    "name": "TODO-1"',
            "  }",
            "}",
            "```",
        ].join("\n"),
    );
});

test("renders compact and expanded RestrictedPython execution results", () => {
    const code = 'for name in ["A", "B"]:\n    print(name)';
    const compact = renderExecMarkdown({
        code,
        committed: false,
        expanded: false,
    });
    const expanded = renderExecMarkdown({
        code,
        committed: true,
        expanded: true,
        response: "A\nB",
    });

    assert.match(compact, /^\*\*Frappe Exec ▲ \(rolled back\)\*\*/u);
    assert.match(compact, /for name in \["A", "B"\]: print\(name\)/u);
    assert.match(expanded, /^\*\*Frappe Exec ▲ \(committed\)\*\*/u);
    assert.match(expanded, /```python\nfor name[\s\S]*print\(name\)\n```/u);
    assert.match(expanded, /```text\nA\nB\n```/u);
});

test("marks failed and truncated calls and uses safe Markdown fences", () => {
    const failed = renderFetchMarkdown({
        expanded: true,
        isError: true,
        method: "DELETE",
        path: "/api/resource/ToDo/TODO-1",
        response: '{"error":"```"}',
    });
    const truncated = renderExecMarkdown({
        code: "print(1)",
        committed: false,
        expanded: false,
        truncated: true,
    });

    assert.match(failed, /^\*\*Frappe API ▲ \(failed\)\*\*/u);
    assert.match(failed, /````text\n\{"error":"```"\}\n````/u);
    assert.match(truncated, /rolled back, truncated/u);
});

test("extracts the response section from tool content", () => {
    assert.equal(
        responseFromToolContent(
            'GET https://erp.example/api/resource/Item\nHTTP 200 OK\n\n{"data":[]}',
        ),
        '{"data":[]}',
    );
    assert.equal(responseFromToolContent("plain output"), "plain output");
});

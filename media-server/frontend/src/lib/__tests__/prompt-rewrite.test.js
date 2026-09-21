import { afterEach, describe, expect, it, vi } from "vitest";
import {
    IMAGE_EDIT_SYSTEM_PROMPT,
    IMAGE_GENERATION_SYSTEM_PROMPT,
    rewritePrompt,
} from "../prompt-rewrite.js";

function jsonResponse(body, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    };
}

function mockFetch(response) {
    const fetchMock = vi.fn(async (url, options = {}) =>
        response(url, options),
    );
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
}

const configuredRequest = {
    prompt: "a misty lighthouse",
    endpoint: "https://llm.example.test/v1/chat/completions",
    apiKey: "test-api-key",
    model: "test-model",
};

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("rewritePrompt", () => {
    it("POSTs the configured endpoint with credentials, model, and the generation prompt", async () => {
        const fetchMock = mockFetch(() =>
            jsonResponse({ choices: [{ message: { content: "rewritten" } }] }),
        );

        await rewritePrompt({ ...configuredRequest, hasImages: false });

        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe(configuredRequest.endpoint);
        expect(options).toMatchObject({
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: "Bearer test-api-key",
            },
        });
        expect(JSON.parse(options.body)).toEqual({
            model: "test-model",
            messages: [
                { role: "system", content: IMAGE_GENERATION_SYSTEM_PROMPT },
                { role: "user", content: "a misty lighthouse" },
            ],
        });
    });

    it("uses the image editing system prompt when source images are present", async () => {
        const fetchMock = mockFetch(() =>
            jsonResponse({ choices: [{ message: { content: "rewritten" } }] }),
        );

        await rewritePrompt({ ...configuredRequest, hasImages: true });

        const [, options] = fetchMock.mock.calls[0];
        expect(JSON.parse(options.body).messages[0]).toEqual({
            role: "system",
            content: IMAGE_EDIT_SYSTEM_PROMPT,
        });
    });

    it("sends supplied source images as OpenAI-compatible vision content", async () => {
        const fetchMock = mockFetch(() =>
            jsonResponse({ choices: [{ message: { content: "rewritten" } }] }),
        );
        const images = [
            "data:image/png;base64,FIRST",
            "data:image/jpeg;base64,SECOND",
        ];

        await rewritePrompt({
            ...configuredRequest,
            hasImages: true,
            images,
        });

        const [, options] = fetchMock.mock.calls[0];
        expect(JSON.parse(options.body).messages[1].content).toEqual([
            { type: "text", text: configuredRequest.prompt },
            { type: "image_url", image_url: { url: images[0] } },
            { type: "image_url", image_url: { url: images[1] } },
        ]);
    });

    it("keeps user content as a string when no source images are provided", async () => {
        const fetchMock = mockFetch(() =>
            jsonResponse({ choices: [{ message: { content: "rewritten" } }] }),
        );

        await rewritePrompt({ ...configuredRequest, hasImages: false });

        const [, options] = fetchMock.mock.calls[0];
        expect(JSON.parse(options.body).messages[1].content).toBe(
            configuredRequest.prompt,
        );
    });

    it("returns the trimmed first completion message", async () => {
        mockFetch(() =>
            jsonResponse({
                choices: [
                    { message: { content: "  enhanced lighthouse  \n" } },
                ],
            }),
        );

        await expect(
            rewritePrompt({ ...configuredRequest, hasImages: false }),
        ).resolves.toBe("enhanced lighthouse");
    });

    it("omits the model when the endpoint selects a default", async () => {
        const fetchMock = mockFetch(() =>
            jsonResponse({ choices: [{ message: { content: "rewritten" } }] }),
        );

        await rewritePrompt({
            ...configuredRequest,
            model: "",
            hasImages: false,
        });

        const [, options] = fetchMock.mock.calls[0];
        expect(JSON.parse(options.body)).toEqual({
            messages: [
                { role: "system", content: IMAGE_GENERATION_SYSTEM_PROMPT },
                { role: "user", content: "a misty lighthouse" },
            ],
        });
    });

    it.each([
        ["endpoint", { ...configuredRequest, endpoint: "" }, "endpoint"],
        ["API key", { ...configuredRequest, apiKey: "" }, "API key"],
    ])(
        "rejects a clear error when the %s is missing",
        async (_, request, error) => {
            await expect(rewritePrompt(request)).rejects.toThrow(error);
        },
    );

    it("rejects with the HTTP error detail", async () => {
        mockFetch(() => jsonResponse({ detail: "invalid API key" }, 401));

        await expect(rewritePrompt(configuredRequest)).rejects.toThrow(
            "invalid API key",
        );
    });

    it.each([
        [undefined],
        [{}],
        [{ choices: [] }],
        [{ choices: [{ message: {} }] }],
        [{ choices: [{ message: { content: "   " } }] }],
    ])(
        "rejects an empty or malformed completion response: %o",
        async (body) => {
            mockFetch(() => jsonResponse(body));

            await expect(rewritePrompt(configuredRequest)).rejects.toThrow(
                /completion response/i,
            );
        },
    );

    it("forwards the caller AbortSignal to fetch", async () => {
        const fetchMock = mockFetch(() =>
            jsonResponse({ choices: [{ message: { content: "rewritten" } }] }),
        );
        const controller = new AbortController();

        await rewritePrompt({
            ...configuredRequest,
            signal: controller.signal,
        });

        const [, options] = fetchMock.mock.calls[0];
        expect(options.signal).toBe(controller.signal);
    });
});
